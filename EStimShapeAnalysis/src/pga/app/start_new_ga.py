from clat.util import time_util
from src.startup import context


def main():
    context.ga_config.db_util.update_ready_gas_and_generations_info(context.ga_name, 0)
    context.ga_config.db_util.conn.truncate("StimGaInfo")
    context.ga_config.db_util.conn.truncate("LineageGaInfo")
    context.ga_config.db_util.conn.truncate("StimSpec")
    context.ga_config.db_util.conn.truncate("TaskToDo")
    context.ga_config.db_util.conn.truncate("TaskDone")
    context.ga_config.db_util.conn.truncate("BehMsg")
    context.ga_config.db_util.conn.truncate("ChannelResponses")
    context.ga_config.db_util.conn.truncate("CurrentExperiments")
    context.ga_config.db_util.conn.truncate("ClusterInfo")


if __name__ == "__main__":
    main()

