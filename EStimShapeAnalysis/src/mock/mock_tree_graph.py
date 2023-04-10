from __future__ import annotations

import os

import PIL
import plotly.graph_objects as go
import pyperclip
from PIL.Image import Image
from dash import dash, dcc, html, Output, Input

from src.tree_graph.tree_graph import TreeGraph, TreeGraphApp
from src.util.connection import Connection

import xml.etree.ElementTree as ET

from tests.tree_graph.colored_test_tree_graph import ColoredTreeGraph

conn = Connection("allen_estimshape_dev_221110")


class MockTreeGraphApp(TreeGraphApp):
    def __init__(self):
        self.app = dash.Dash("Tree Graphs")
        self._update_app()
        self.run()

    def _update_app(self):
        # Define the lineage_id options
        lineage_id_options = get_all_lineages()

        # Create the app layout
        self.app.layout = html.Div(
            [
                dcc.Dropdown(id="lineage-id", options=lineage_id_options, value=1),
                dcc.Graph(id="tree", clear_on_unhover=True),
                html.Div(id="clipboard-data"),
                html.Div(id="node-info"),
            ]
        )

        # Define the callback for updating the graph based on the selected lineage_id
        @self.app.callback(
            Output("tree", "figure"),
            Input("lineage-id", "value"),
        )
        def update_graph(lineage_id):
            # modify the figure based on the selected lineage_id
            print(f"Lineage {lineage_id} selected")
            tree_graph = MockTreeGraph(lineage_id)
            return tree_graph.fig

        # Define the callback for click events
        @self.app.callback(
            Output("node-info", "children"), Input("tree", "clickData")
        )
        def display_click_data(clickData):
            if clickData:
                node_label = clickData["points"][0]["text"]
                print(f"Node {node_label} clicked")  # Print the node information
                return f"Node {node_label} clicked"
            else:
                return ""

        # Define the callback for copying to clipboard
        @self.app.callback(
            Output("clipboard-data", "children"), Input("tree", "clickData")
        )
        def copy_to_clipboard(clickData):
            if clickData:
                node_label = clickData["points"][0]["text"]
                print(f"Node {node_label} copied to clipboard")  # Print the node information
                pyperclip.copy(node_label)
                return f"Node {node_label} copied to clipboard"
            else:
                return ""


def get_all_lineages():
    conn.execute("SELECT lineage_id FROM LineageGaInfo ORDER BY regime_score desc")
    lineage_ids_as_list_of_tuples = conn.fetch_all()
    lineage_ids = [lineage_id[0] for lineage_id in lineage_ids_as_list_of_tuples]
    return lineage_ids


class MockTreeGraph(ColoredTreeGraph):
    def __init__(self, lineage_id):
        tree_spec = fetch_tree_spec(lineage_id)
        edges = recursive_tree_to_edges(tree_spec)
        stim_ids = {stim_id for edge in edges for stim_id in edge}
        y_values_for_stim_ids = fetch_responses_for(stim_ids)
        image_folder = "/home/r2_allen/Documents/EStimShape/dev_221110/pngs_dev_221110"
        edge_colors = get_edge_colors(edges)
        super().__init__(y_values_for_stim_ids, edges, edge_colors, image_folder)

    def _get_image(self, stim_id):
        for filename in os.listdir(self.image_folder):
            if filename.startswith(str(stim_id)) and filename.endswith('.png'):
                img_path = os.path.join(self.image_folder, filename)
                print(img_path)
                img = PIL.Image.open(img_path)
                return img
        return None


def get_edge_colors(edges: list[tuple[int, int]]):
    colors_for_regimes = {
        "RegimeZero": "black",
        "RegimeOne": "red",
        "RegimeTwo": "blue",
        "RegimeThree": "green",
        "RegimeFour": "yellow",
    }

    edge_colors = {}
    for edge in edges:
        regime = fetch_regime_for_stim_id(edge[1])
        color = colors_for_regimes[regime]
        edge_colors[edge] = color

    return edge_colors


def fetch_regime_for_stim_id(stim_id):
    conn.execute("SELECT stim_type from StimGaInfo where stim_id = %s", (stim_id,))
    stim_type = conn.fetch_one()
    return stim_type


def fetch_responses_for(stim_ids):
    responses = {}
    for stim_id in stim_ids:
        conn.execute("SELECT response from StimGaInfo where stim_id = %s", (stim_id,))
        response = conn.fetch_one()
        responses[stim_id] = float(response)
    return responses


def recursive_tree_to_edges(tree):
    edges = []
    if "children" in tree:
        for child in tree["children"]:
            edges.append((tree["identifier"], child["identifier"]))
            edges.extend(recursive_tree_to_edges(child))
    return edges


def fetch_tree_spec(lineage_id):
    conn.execute("SELECT tree_spec from LineageGaInfo where lineage_id = %s", (lineage_id,))
    tree_spec = conn.fetch_one()
    tree_spec = parse_recursive_xml(tree_spec)
    return tree_spec


def parse_recursive_xml(xml_string):
    root = ET.fromstring(xml_string)
    return _parse_recursive_xml_helper(root)


def _parse_recursive_xml_helper(elem):
    result = {}
    if elem.tag == "GABranch":
        children = []
        for child_elem in elem.findall("children/GABranch"):
            children.append(_parse_recursive_xml_helper(child_elem))
        result["children"] = children
        result["identifier"] = int(elem.find("identifier").text)
    return result


def main():
    app = MockTreeGraphApp()
    app.run()


if __name__ == "main":
    main()