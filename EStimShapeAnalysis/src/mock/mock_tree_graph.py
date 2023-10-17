from __future__ import annotations

import os

import PIL
import plotly.graph_objects as go
import pyperclip
import xmltodict
from PIL.Image import Image
from dash import dash, dcc, html, Output, Input, State
import dash as DASH
from dash.exceptions import PreventUpdate
from plotly.graph_objs import Scatter
from ast import literal_eval as make_tuple
from src.tree_graph.tree_graph import TreeGraph, TreeGraphApp
from clat.util.connection import Connection

import xml.etree.ElementTree as ET

from tests.tree_graph.colored_test_tree_graph import ColoredTreeGraph

conn = Connection("allen_estimshape_dev_230519")


def fetch_components_to_preserve_for_stim_id(stim_id):
    try:
        conn.execute("SELECT data from StimSpec where id = %s", (stim_id,))
        mstick_data = conn.fetch_one()
        mstick_data_dict = xmltodict.parse(mstick_data)
        components_to_preserve = mstick_data_dict["AllenMStickData"]["componentsToPreserve"]
    except:
        components_to_preserve = None
    return components_to_preserve


def fetch_components_exploring_for_stim_id(stim_id):
    try:
        conn.execute("SELECT data from StimSpec where id = %s", (stim_id,))
        mstick_data = conn.fetch_one()
        mstick_data_dict = xmltodict.parse(mstick_data)
        components_exploring = mstick_data_dict["AllenMStickData"]["componentsExploring"]
    except:
        components_exploring = None
    return components_exploring


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
                dcc.Store(id="zoom-factor", data=100),
                html.Button("Increase Size", id="increase-size-btn", n_clicks=0),
                html.Button("Decrease Size", id="decrease-size-btn", n_clicks=0),
                dash.dcc.Store(id='highlight-data', data=[]),
                html.Button("Reset Highlight", id="reset-highlight-btn", n_clicks=0),
            ]
        )

        # Define the callback for updating the graph based on the selected lineage_id
        @self.app.callback(
            Output("tree", "figure"),
            Input("lineage-id", "value"),
            Input("zoom-factor", "data"),
            Input("highlight-data", "data"),
        )
        def update_graph(lineage_id, zoom_factor, nodes_to_highlight):
            ctx = DASH.callback_context
            if ctx.triggered:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if input_id == "lineage-id":
                    return update_lineage(lineage_id)
                elif input_id == "zoom-factor":
                    return self.tree_graph.update_image_size(zoom_factor)
                elif input_id == "highlight-data":
                    return self.tree_graph.highlight_nodes(nodes_to_highlight)
                else:
                    return dash.no_update
            else:
                return dash.no_update

        def update_lineage(lineage_id):
            # modify the figure based on the selected lineage_id
            print(f"Lineage {lineage_id} selected")
            self.tree_graph = MockTreeGraph(lineage_id)
            self.tree_graph.fig.update_xaxes(autorange=True)
            self.tree_graph.fig.update_yaxes(autorange=True)
            return self.tree_graph.fig

        @self.app.callback(
            Output("zoom-factor", "data"),
            Input("increase-size-btn", "n_clicks"),
            Input("decrease-size-btn", "n_clicks"),
            State("zoom-factor", "data"),
        )
        def update_image_size_on_button_press(increase_clicks, decrease_clicks, zoom_factor):
            ctx = DASH.callback_context

            if ctx.triggered:
                button_id = ctx.triggered[0]["prop_id"].split(".")[0]
                if button_id == "increase-size-btn":
                    zoom_factor = zoom_factor + 5
                    return zoom_factor
                elif button_id == "decrease-size-btn":
                    zoom_factor = zoom_factor - 5
                    return zoom_factor

            raise PreventUpdate

        @self.app.callback(
            Output("highlight-data", "data"),
            Input("tree", "clickData"),
            Input("reset-highlight-btn", "n_clicks"),
        )
        def update_highlight_data(clickData, reset_clicks):
            ctx = DASH.callback_context
            if ctx.triggered:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if input_id == "tree":
                    nodes_to_highlight = []
                    if clickData:
                        stim_id = clickData["points"][0]["text"]
                        nodes_to_highlight.append(float(stim_id))
                        return nodes_to_highlight
                    else:
                        return dash.no_update
                elif input_id == "reset-highlight-btn":
                    return self.tree_graph.stim_ids
                else:
                    return dash.no_update


        # Define the callback for click events
        @self.app.callback(
            Output("node-info", "children"),
            Input("tree", "clickData")
        )
        def display_click_data(clickData):
            if clickData:
                node_label = clickData["points"][0]["text"]
                component_print = []
                # Print Parent INfo
                parent_id = fetch_parent_id_for_stim_id(node_label)
                component_print.append(f"ParentID: {parent_id}\n")
                component_print.append(html.Br())

                # Print Regime Info
                stim_type = fetch_regime_for_stim_id(node_label)
                component_print.append(f"StimType: {stim_type}\n")
                component_print.append(html.Br())

                # If Regime TWO
                if stim_type == "RegimeTwo":
                    components_to_preserve = fetch_components_to_preserve_for_stim_id(node_label)
                    component_print.append(f"Components to Preserve: {components_to_preserve}\n")
                    component_print.append(html.Br())

                # IF Regime THREE
                if stim_type == "RegimeThree":
                    try:
                        components_exploring = fetch_components_exploring_for_stim_id(node_label)
                        component_print.append(f"Components Exploring: {components_exploring}\n")
                        component_print.append(html.Br())
                    except:
                        component_print.append(f"Components Exploring: All\n")

                # Print Shaft Info
                mstick_data = fetch_shaft_data_for_mstick(node_label)
                for component in mstick_data:
                    component_print.append(f"{component}\n")
                    component_print.append(html.Br())

                return component_print
            else:
                return ""

        # Define the callback for copying to clipboard
        @self.app.callback(
            Output("clipboard-data", "children"),
            Input("tree", "clickData")
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
    query = """
    SELECT LineageGaInfo.lineage_id
    FROM (
        SELECT lineage_id, MAX(gen_id) as max_gen_id
        FROM LineageGaInfo
        GROUP BY lineage_id
    ) AS unique_lineages
    JOIN LineageGaInfo ON LineageGaInfo.lineage_id = unique_lineages.lineage_id AND LineageGaInfo.gen_id = unique_lineages.max_gen_id
    WHERE LineageGaInfo.regime > 0
    ORDER BY LineageGaInfo.regime DESC
    LIMIT 10
    """
    conn.execute(query)
    lineage_ids_as_list_of_tuples = conn.fetch_all()
    lineage_ids = [lineage_id[0] for lineage_id in lineage_ids_as_list_of_tuples]
    return lineage_ids


def fetch_children_ids_for_stim_id(param):
    conn.execute("SELECT stim_id FROM StimGaInfo WHERE parent_id = %s", (param,))
    children_ids_as_list_of_tuples = conn.fetch_all()
    children_ids = [child_id[0] for child_id in children_ids_as_list_of_tuples]
    return children_ids


class MockTreeGraph(ColoredTreeGraph):
    def __init__(self, lineage_id):
        tree_spec = fetch_tree_spec(lineage_id)
        edges = recursive_tree_to_edges(tree_spec)
        self.stim_ids = [stim_id for edge in edges for stim_id in edge]
        y_values_for_stim_ids = fetch_responses_for(self.stim_ids)
        image_folder = "/home/r2_allen/Documents/EStimShape/dev_230519/pngs_dev_230519"
        edge_colors = get_edge_colors(edges)
        super().__init__(y_values_for_stim_ids, edges, edge_colors, image_folder)
        self.highlighted_nodes = []

    def update_image_size(self, size):
        print(f"Updating images with size {size}")
        for img in self.fig.layout.images:
            img.sizex = size
            img.sizey = size

        # self.node_trace.update(marker_size=size/2)
        self.fig.data[0].update(marker_size=size/4)

        return self.fig

    def highlight_nodes(self, nodes_to_highlight):

        # Highlight selected node and the parent to 100% opacit
        # and set everything else to 0.1 opacity
        parent_id = fetch_parent_id_for_stim_id(nodes_to_highlight[0])
        children_ids = fetch_children_ids_for_stim_id(nodes_to_highlight[0])
        for image_index, img in enumerate(self.fig.layout.images):
            try:
                if int(img.name) in nodes_to_highlight or int(img.name) == int(parent_id):
                    img.opacity = 1
                elif int(img.name) in children_ids:
                    img.opacity = 0.5
                else:
                    img.opacity = 0.05
            except:
                pass


        self.fig.update_layout(images=self.fig.layout.images)

        for i, edge in enumerate(self.fig.data[1:-1]):
            edge_nodes = make_tuple(edge.name)
            try:
                if edge_nodes[0] in nodes_to_highlight or edge_nodes[1] in nodes_to_highlight:
                    edge.update(opacity=1)
                else:
                    edge.update(opacity=0.1)
            except:
                pass
        self.highlighted_nodes = nodes_to_highlight

        return self.fig

    def reset_highlighted_nodes(self):
        for image_index, img in enumerate(self.fig.layout.images):
            img.opacity = 1

        self.fig.update_layout(images=self.fig.layout.images)

        for i, edge in enumerate(self.fig.data[1:-1]):
            edge.update(opacity=1)
        self.highlighted_nodes = []

    def _get_image(self, stim_id):
        for filename in os.listdir(self.image_folder):
            if filename.startswith(str(stim_id)) and filename.endswith('.png'):
                img_path = os.path.join(self.image_folder, filename)
                img = PIL.Image.open(img_path)
                return img
        return None


def get_edge_colors(edges: list[tuple[int, int]]):
    colors_for_regimes = {
        "REGIME_ZERO": "black",
        "REGIME_ONE": "red",
        "REGIME_TWO": "blue",
        "REGIME_THREE": "green",
        "REGIME_FOUR": "yellow",
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


def fetch_parent_id_for_stim_id(stim_id):
    conn.execute("SELECT parent_id from StimGaInfo where stim_id = %s", (stim_id,))
    parent_id = conn.fetch_one()
    return parent_id


def fetch_responses_for(stim_ids):
    responses = {}
    for stim_id in stim_ids:
        conn.execute("SELECT response from StimGaInfo where stim_id = %s", (stim_id,))
        response = conn.fetch_one()
        responses[stim_id] = float(response)
    return responses


def fetch_shaft_data_for_mstick(stim_id):
    conn.execute("SELECT data from StimSpec where id = %s", (stim_id,))
    mstick_data = conn.fetch_one()
    mstick_data_dict = xmltodict.parse(mstick_data)
    shaft_data = mstick_data_dict["AllenMStickData"]["shaftData"]["ShaftData"]
    return shaft_data


def fetch_tree_spec(lineage_id):
    conn.execute("SELECT tree_spec from LineageGaInfo where lineage_id = %s ORDER BY gen_id DESC LIMIT 1", (lineage_id,))
    tree_spec = conn.fetch_one()
    tree_spec = _parse_recursive_xml(tree_spec)
    return tree_spec


def recursive_tree_to_edges(tree):
    edges = []
    if "children" in tree:
        for child in tree["children"]:
            edges.append((tree["identifier"], child["identifier"]))
            edges.extend(recursive_tree_to_edges(child))
    return edges


def _parse_recursive_xml(xml_string):
    root = ET.fromstring(xml_string)
    return _parse_recursive_node(root)


def _parse_recursive_node(elem):
    children = []
    for child_elem in elem.findall('Node'):
        children.append(_parse_recursive_node(child_elem))

    return {
        "identifier": int(elem.text),
        "children": children
    }

def main():
    app = MockTreeGraphApp()
    app.run()


if __name__ == "__main__":
    main()
