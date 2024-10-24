from src.pga.genetic_algorithm import GeneticAlgorithm


class AlexNetGeneticAlgorithm(GeneticAlgorithm):
    num_catch_trials = 0
    def run(self):
        self.process_responses()
        self.gen_id = self._read_gen_id()
        self.gen_id += 1

        if self.gen_id == 1:
            self._update_db_with_new_experiment()
            self._run_first_generation()
            self.response_parser.parse_to_db(self.name)
            self.response_processor.process_to_db(self.name)
        elif self.gen_id > 1:
            # recover experiment_id
            self.experiment_id = self.db_util.read_current_experiment_id(self.name)
            self._construct_lineages_from_db()
            self._transition_lineages_if_needed()

            self._run_next_generation()
        else:
            raise ValueError("gen_id must be >= 1")

        self._update_db()
        self.trial_generator.generate_trials(experiment_id=self.experiment_id, generation=self.gen_id)
        self.response_parser.parse_to_db(self.name)
        self.response_processor.process_to_db(self.name)

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
                try:
                    self.db_util.read_stim_ga_info_entry(stim.id)
                except Exception:
                    # If the stim is not in the db, write it
                    self.db_util.write_stim_ga_info(stim_id=stim.id, parent_id=stim.parent_id,
                                                    lineage_id=lineage.id,
                                                    stim_type=stim.mutation_type,
                                                    mutation_magnitude=stim.mutation_magnitude,
                                                    gen_id=self.gen_id)

