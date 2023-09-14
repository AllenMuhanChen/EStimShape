from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List

from mysql.connector import DatabaseError

from intan.spike_parsing import ResponseParser
from intan.response_processing import ResponseProcessor
from newga.ga_classes import LineageDistributor, Node, Stimulus, LineageFactory
from newga.lineage_selection import ClassicLineageDistributor
from newga.regime_type import RegimeType
from newga.multi_ga_db_util import MultiGaDbUtil
from src.newga.ga_classes import Regime, Lineage
from util import time_util


@dataclass(kw_only=True)
class GeneticAlgorithm:
    # Dependencies
    name: str
    regimes: List[Regime]
    db_util: MultiGaDbUtil
    trials_per_generation: int
    lineage_distributor: ClassicLineageDistributor
    response_parser: ResponseParser
    response_processor: ResponseProcessor

    # Instance Variables
    experiment_id: int = field(init=False, default=None)
    gen_id: int = field(init=False, default=0)
    lineages: List[Lineage] = field(init=False, default_factory=list)

    def process_responses(self):
        # Could be run outside of this class
        self.response_parser.parse_to_db(self.name)
        self.response_processor.process_to_db(self.name)

    def run(self):
        self.gen_id = self._read_gen_id()
        self.gen_id += 1

        if self.gen_id == 1:
            self._update_db_with_new_experiment()
            self._run_first_generation()
        elif self.gen_id > 1:
            # recover experiment_id
            self.experiment_id = self.db_util.read_current_experiment_id(self.name)
            # Could be run outside of this class
            self.response_parser.parse_to_db(self.name)
            self.response_processor.process_to_db(self.name)
            #

            self._construct_lineages_from_db()
            self._transition_lineages_if_needed()

            self._run_next_generation()
        else:
            raise ValueError("gen_id must be >= 1")

        self._update_db()

    def _transition_lineages_if_needed(self):
        for lineage in self.lineages:
            lineage.transition_regimes_if_needed()

    def _update_db_with_new_experiment(self):
        self.experiment_id = time_util.now()
        self.db_util.write_new_experiment_id(self.name, self.experiment_id)

    def _read_gen_id(self):
        try:
            gen_id_for_ga = self.db_util.read_ready_gas_and_generations_info()
            return gen_id_for_ga[self.name]
        except:
            raise DatabaseError("Cannot read gen_id for ga from InternalState table. ")

    def _run_first_generation(self):
        # Initialize lineages
        for trial in range(self.trials_per_generation):
            self._create_lineage()
            time.sleep(1 / 1_000)

        # for lineage in self.lineages:
        #     lineage.age_in_generations += 1

    def _run_next_generation(self):
        num_trials_for_lineages = self.lineage_distributor.get_num_trials_for_lineages(self.lineages)
        # sum all trials:
        print("num_trials_for_lineages", sum(num_trials_for_lineages.values()))
        sum_of_trials_added = 0
        for lineage, num_trials in num_trials_for_lineages.items():
            sum_of_trials_added += num_trials
            # lineage distributor may create new lineages for new regime zero stimuli
            # We should check for them here.
            if lineage not in self.lineages:
                self.lineages.append(lineage)
            else:
                if num_trials > 0:
                    initial_size = len(lineage.stimuli)
                    print("Adding ", num_trials, " trials to lineage ", lineage.id)
                    lineage.generate_new_batch(num_trials)
                    print("Added ", len(lineage.stimuli) - initial_size, " trials to lineage ", lineage.id)
        print("sum_of_trials_added", sum_of_trials_added)

    def _create_lineage(self):
        new_lineage = LineageFactory.create_new_lineage(regimes=self.regimes)
        self.lineages.append(new_lineage)
        return new_lineage

    def _construct_lineages_from_db(self):
        def stim_id_to_stimulus(stim_id: int) -> Stimulus:
            stim_ga_info_entry = self.db_util.read_stim_ga_info_entry(stim_id)
            mutation_type = stim_ga_info_entry.stim_type
            mutation_magnitude = stim_ga_info_entry.mutation_magnitude
            response = stim_ga_info_entry.response
            response_vector = self.response_processor.fetch_response_vector_for(stim_id, ga_name=self.name)
            gen_id = stim_ga_info_entry.gen_id
            return Stimulus(stim_id, mutation_type, response_vector=response_vector, driving_response=response,
                            mutation_magnitude=mutation_magnitude, gen_id=gen_id)

        def add_parent_to_stimulus(stim: Node, parent: Node):
            stim.data.parent_id = parent.data.id

        # Read lineageIds from this experiment_id and previous generation
        lineage_ga_info_entries_for_this_generation = self.db_util.read_lineage_ga_info_for_experiment_id_and_gen_id(
            self.experiment_id, self.gen_id - 1)
        for lineage_entry in lineage_ga_info_entries_for_this_generation:
            # Reconstruct tree of Stimulus objects from a tree_spec of stim_ids
            tree_spec = lineage_entry.tree_spec
            tree_of_stim_ids = Node.from_xml(tree_spec)
            tree_of_stim_ids = tree_of_stim_ids.new_tree_from_function(lambda id: int(id))
            tree_of_stimuli = tree_of_stim_ids.new_tree_from_function(stim_id_to_stimulus)
            tree_of_stimuli.have_parent_apply_to_children(add_parent_to_stimulus)
            current_regime_index = int(lineage_entry.regime)

            reconstructed_lineage = (
                LineageFactory.create_lineage_from_tree(tree_of_stimuli,
                                                        regimes=self.regimes,
                                                        current_regime_index=current_regime_index,
                                                        gen_id=self.gen_id))
            self.lineages.append(reconstructed_lineage)

    def _update_db(self) -> None:
        # Write lineages - instructions for Java side of GA
        for lineage in self.lineages:
            id_tree = lineage.tree.new_tree_from_function(lambda stimulus: stimulus.id)
            self.db_util.write_lineage_ga_info(lineage.id, id_tree.to_xml(), lineage.lineage_data, self.experiment_id,
                                               self.gen_id,
                                               lineage.current_regime_index)

        # Write stimuli
        for lineage in self.lineages:
            for stim in lineage.stimuli:
                self.db_util.write_stim_ga_info(stim_id=stim.id, parent_id=stim.parent_id, lineage_id=lineage.id,
                                                stim_type=stim.mutation_type,
                                                mutation_magnitude=stim.mutation_magnitude,
                                                gen_id=self.gen_id)

        # Update generations
        # self.db_util.update_ready_gas_and_generations_info(self.name, self.gen_id)

    # def _update_lineages_with_new_responses(self):
    #     for lineage in self.lineages:
    #         for stim in lineage.stimuli:
    #             stim.response_vector = self.db_util.read_responses_for(stim.id)
    #             stim.response_rate = self.db_util.read_driving_response(stim.id)
