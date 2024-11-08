from unittest import TestCase

from src.tree_graph.tree_graph_app import TreeGraphApp
from tree_graph.tree_graph import ColoredTreeGraph


class TestColoredTreeGraph(TestCase):
    def test_create_colored_edges(self):
        # Input dictionary with stim_id as keys and y positions as values
        stim_id_y_positions = {
            1: 0,
            2: 1,
            3: 1,
            4: 2,
            5: 2,
            6: 0,
            7: 2,
        }

        edges = [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6), (3, 7)]
        edge_colors = {(1, 2): "red", (1, 3): "blue", (2, 4): "green", (2, 5): "yellow", (3, 6): "purple",
                       (3, 7): "orange"}

        image_folder = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/tree_graph/test_pngs"
        colored_tree_graph = ColoredTreeGraph(stim_id_y_positions, edges, edge_colors, image_folder)
        app = TreeGraphApp(colored_tree_graph)
        self.app = app
        self.app.run()
