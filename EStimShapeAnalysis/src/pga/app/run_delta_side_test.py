from src.startup import context


def main():
    ga = context.ga_config.make_genetic_algorithm()
    name = ga.name

    ga.gen_id = ga._read_gen_id()
    ga.gen_id += 1
    ga.experiment_id = ga.db_util.read_current_experiment_id(name)

    ga.response_processor.process_to_db(name)
    ga._construct_lineages_from_db()

    delta_side_test = next(
        st for st in ga.side_tests
        if type(st).__name__ == 'EStimVariantDeltaSideTest'
    )
    delta_side_test.run(ga.lineages, ga.gen_id)

    ga._update_db()
    ga.trial_generator.generate_trials(experiment_id=ga.experiment_id, generation=ga.gen_id)


if __name__ == "__main__":
    main()
