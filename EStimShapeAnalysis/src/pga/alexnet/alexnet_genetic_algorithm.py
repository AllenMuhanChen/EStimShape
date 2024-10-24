from src.pga.genetic_algorithm import GeneticAlgorithm


class AlexNetGeneticAlgorithm(GeneticAlgorithm):
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
