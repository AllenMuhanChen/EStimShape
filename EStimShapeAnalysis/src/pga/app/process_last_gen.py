from src.startup import context


def main():
    ga = context.ga_config.make_genetic_algorithm()
    parser = ga.response_parser
    parser.parse_to_db(context.ga_name)
    processor = ga.response_processor
    processor.process_to_db(context.ga_name)


if __name__ == "__main__":
    main()
