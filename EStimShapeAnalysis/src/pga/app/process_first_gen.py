from src.startup import config


def main():
    ga = config.ga_config.make_genetic_algorithm()
    parser = ga.response_parser
    parser.parse_to_db(config.ga_name)
    processor = ga.response_processor
    processor.process_to_db(config.ga_name)

if __name__ == "__main__":
    main()
