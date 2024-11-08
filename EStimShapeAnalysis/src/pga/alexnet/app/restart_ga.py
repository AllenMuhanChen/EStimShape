import src.tree_graph.ga_tree_graph
from src.pga.alexnet import alexnet_context


def main():
    alexnet_context.ga_config.db_util.update_ready_gas_and_generations_info(alexnet_context.ga_name, 0)
    src.tree_graph.ga_tree_graph.conn.truncate("StimGaInfo")
    src.tree_graph.ga_tree_graph.conn.truncate("LineageGaInfo")
    src.tree_graph.ga_tree_graph.conn.truncate("StimSpec")
    src.tree_graph.ga_tree_graph.conn.truncate("CurrentExperiments")
    src.tree_graph.ga_tree_graph.conn.truncate("UnitActivations")
    src.tree_graph.ga_tree_graph.conn.truncate("StimPath")

if __name__ == "__main__":
    main()