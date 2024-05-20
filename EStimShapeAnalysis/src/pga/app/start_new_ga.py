from clat.util import time_util
from src.startup import config


def main():
    config.ga_config.db_util.update_ready_gas_and_generations_info(config.ga_name, 0)
    config.ga_config.db_util.conn.truncate("StimGaInfo")
    config.ga_config.db_util.conn.truncate("LineageGaInfo")
    config.ga_config.db_util.conn.truncate("StimSpec")
    config.ga_config.db_util.conn.truncate("TaskToDo")
    config.ga_config.db_util.conn.truncate("TaskDone")
    config.ga_config.db_util.conn.truncate("BehMsg")
    config.ga_config.db_util.conn.truncate("ChannelResponses")
    config.ga_config.db_util.conn.truncate("CurrentExperiments")
    config.ga_config.db_util.conn.truncate("ClusterInfo")


if __name__ == "__main__":
    main()

