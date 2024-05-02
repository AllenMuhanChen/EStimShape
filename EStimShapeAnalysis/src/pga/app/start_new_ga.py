from startup import config


def main():
    config.ga_config.db_util.update_ready_gas_and_generations_info(config.ga_name, 0)


if __name__ == "__main__":
    main()

