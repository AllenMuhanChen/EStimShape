from clat.util import time_util

import src.tree_graph.ga_tree_graph
from src.startup import context


def main():
    context.ga_config.db_util.update_ready_gas_and_generations_info(context.ga_name, 0)
    src.tree_graph.ga_tree_graph.conn.truncate("StimGaInfo")
    src.tree_graph.ga_tree_graph.conn.truncate("LineageGaInfo")
    src.tree_graph.ga_tree_graph.conn.truncate("StimSpec")
    src.tree_graph.ga_tree_graph.conn.truncate("TaskToDo")
    src.tree_graph.ga_tree_graph.conn.truncate("TaskDone")
    src.tree_graph.ga_tree_graph.conn.truncate("BehMsg")
    src.tree_graph.ga_tree_graph.conn.truncate("ChannelResponses")
    src.tree_graph.ga_tree_graph.conn.truncate("CurrentExperiments")
    src.tree_graph.ga_tree_graph.conn.truncate("ClusterInfo")


if __name__ == "__main__":
    main()

