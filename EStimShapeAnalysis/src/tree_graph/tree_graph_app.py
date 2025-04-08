from __future__ import annotations

import dash
import pyperclip
from dash import html, dcc, Output, Input


class TreeGraphApp:
    def __init__(self, tree_graph):
        self.tree_graph = tree_graph
        self.app = dash.Dash("Tree Graph")
        self._update_app(tree_graph.fig)
        self.run()

    def run(self):
        self.app.run_server(port=8054)

    def _update_app(self, fig):

        # Create the app layout
        self.app.layout = html.Div(
            [
                dcc.Graph(id="tree",
                          figure=fig, clear_on_unhover=True,
                          autosize=False, ),
                html.Div(id="clipboard-data"),
                html.Div(id="node-info"),
            ]
        )

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
