from src.startup import context
from src.analysis.ga.repo_ga_response_update import update_repository_with_ga_responses


def main():
    ga = context.ga_config.make_genetic_algorithm()
    parser = ga.response_parser
    parser.parse_to_db(context.ga_name)
    processor = ga.response_processor
    processor.process_to_db(context.ga_name)

    # GA Responses are now stored; push them into the repository (best-effort).
    update_repository_with_ga_responses()


if __name__ == "__main__":
    main()
