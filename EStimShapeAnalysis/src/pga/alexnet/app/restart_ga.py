from src.pga.alexnet import alexnet_context


def main():
    alexnet_context.ga_config.db_util.update_ready_gas_and_generations_info(alexnet_context.ga_name, 0)
    alexnet_context.ga_config.db_util.conn.truncate("StimGaInfo")
    alexnet_context.ga_config.db_util.conn.truncate("LineageGaInfo")
    alexnet_context.ga_config.db_util.conn.truncate("StimSpec")
    alexnet_context.ga_config.db_util.conn.truncate("CurrentExperiments")
    alexnet_context.ga_config.db_util.conn.truncate("UnitActivations")
    alexnet_context.ga_config.db_util.conn.truncate("StimPath")

if __name__ == "__main__":
    main()