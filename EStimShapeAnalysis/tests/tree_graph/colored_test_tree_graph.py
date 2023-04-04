from unittest import TestCase
import base64
import io
import os
import subprocess

import dash
from dash import dcc
from dash import html
from dash.dependencies import Input, Output
import networkx as nx
import plotly.graph_objects as go
from PIL import Image
from src.tree_graph import tree_graph
from src.tree_graph.tree_graph import TreeGraph, TreeGraphApp


class ColoredTreeGraph(TreeGraph):
    def __init__(self, y_values_for_stim_ids, edges, edge_colors):
        self.edge_colors = edge_colors
        super().__init__(y_values_for_stim_ids, edges)

    def _create_edges(self, pos, tree):
        print("COLORED EDGES CALLED")
        edge_traces = []
        for edge in tree.edges():
            x = [pos[edge[0]][0], pos[edge[1]][0], None]
            y = [pos[edge[0]][1], pos[edge[1]][1], None]
            color = self.edge_colors[edge]
            edge_trace = go.Scatter(
                x=x,
                y=y,
                mode="lines",
                line=dict(width=2, color=color),
                hoverinfo="none",
            )
            edge_traces.append(edge_trace)
        return edge_traces

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

        colored_tree_graph = ColoredTreeGraph(stim_id_y_positions, edges, edge_colors)
        app = TreeGraphApp(colored_tree_graph)
        self.app = app
        self.app.run()


