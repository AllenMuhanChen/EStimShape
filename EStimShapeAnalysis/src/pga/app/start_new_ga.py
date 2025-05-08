from clat.util import time_util

import src.tree_graph.ga_tree_graph
from src.startup import context


def main():
    context.ga_config.db_util.update_ready_gas_and_generations_info(context.ga_name, 0)
    conn = context.ga_config.connection()
    conn.execute("DELETE FROM CurrentExperiments") # LineageGaInfo, StimGaInfo and ZoomingPhaseSets are cascaded to this
    conn.truncate("StimSpec")
    conn.truncate("TaskToDo")
    conn.truncate("TaskDone")
    conn.truncate("BehMsg")
    conn.truncate("ChannelResponses")
    conn.truncate("ClusterInfo")
    conn.truncate("StimTexture")
    conn.truncate("StimColor")
    conn.truncate("StimSize")



if __name__ == "__main__":
    main()

