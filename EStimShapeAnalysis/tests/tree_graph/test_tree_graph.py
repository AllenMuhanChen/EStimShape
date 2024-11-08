from unittest import TestCase

from PIL.ImageQt import rgb
from dash import dash

from src.tree_graph import tree_graph
from src.tree_graph.tree_graph import TreeGraph
from src.tree_graph.tree_graph_app import TreeGraphApp
import plotly.graph_objects as go



class TreeGraphTest(TestCase):
    def test_create_tree_graph(self):
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

        image_folder = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/tests/tree_graph/test_pngs"
        tg = TreeGraph(stim_id_y_positions, edges, image_folder)
        app = TreeGraphApp(tg)
        app.run()

