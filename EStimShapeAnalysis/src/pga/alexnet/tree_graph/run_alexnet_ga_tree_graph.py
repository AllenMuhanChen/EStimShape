from __future__ import annotations

import dash as DASH
import pyperclip
from dash import dash, dcc, html, Output, Input, State
from dash.exceptions import PreventUpdate

from src.pga.alexnet.tree_graph.alexnet_ga_tree_graph import AlexNetDataAccess
from src.tree_graph.tree_graph_app import TreeGraphApp
from src.tree_graph.ga_tree_graph import GATreeGraph
from src.pga.alexnet import alexnet_context


class AlexNetTreeGraphApp(TreeGraphApp):
    def __init__(self):
        self.data_layer = AlexNetDataAccess(
            conn=alexnet_context.ga_config.connection(),
            image_base_path=alexnet_context.image_path
        )
        self.app = dash.Dash("AlexNet Tree Graphs")
        self._update_app()
        self.run()

    def _update_app(self):
        lineage_id_options = self.data_layer.get_all_lineages()

        self.app.layout = html.Div([
            dcc.Dropdown(id="lineage-id", options=lineage_id_options, value=1),
            dcc.Graph(id="tree", clear_on_unhover=True),
            html.Div(id="clipboard-data"),
            html.Div(id="node-info"),
            dcc.Store(id="zoom-factor", data=100),
            html.Button("Increase Size", id="increase-size-btn", n_clicks=0),
            html.Button("Decrease Size", id="decrease-size-btn", n_clicks=0),
            dash.dcc.Store(id='highlight-data', data=[]),
            html.Button("Reset Highlight", id="reset-highlight-btn", n_clicks=0),
        ])

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
            print(f"Lineage {lineage_id} selected")
            self.tree_graph = GATreeGraph(lineage_id, self.data_layer)
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
                    return zoom_factor + 5
                elif button_id == "decrease-size-btn":
                    return zoom_factor - 5
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
                    if clickData:
                        stim_id = clickData["points"][0]["text"]
                        return [float(stim_id)]
                    return dash.no_update
                elif input_id == "reset-highlight-btn":
                    return self.tree_graph.stim_ids
            return dash.no_update

        @self.app.callback(
            Output("node-info", "children"),
            Input("tree", "clickData")
        )
        def display_click_data(clickData):
            if clickData:
                node_label = clickData["points"][0]["text"]
                component_print = []

                # Get node information
                parent_id = self.data_layer.get_parent_id(node_label)
                stim_type = self.data_layer.get_regime(node_label)
                metadata = self.data_layer.get_metadata(node_label)

                # Print Parent Info
                component_print.append(f"Parent ID: {parent_id}\n")
                component_print.append(html.Br())

                # Print Regime Info
                component_print.append(f"Stim Type: {stim_type}\n")
                component_print.append(html.Br())

                # Print Activation Value
                if "activation" in metadata:
                    component_print.append(f"Activation: {metadata['activation']:.4f}\n")
                    component_print.append(html.Br())

                # Print Mutation Magnitude
                if "mutation_magnitude" in metadata:
                    component_print.append(f"Mutation Magnitude: {metadata['mutation_magnitude']:.4f}\n")
                    component_print.append(html.Br())

                return component_print
            return ""

        @self.app.callback(
            Output("clipboard-data", "children"),
            Input("tree", "clickData")
        )
        def copy_to_clipboard(clickData):
            if clickData:
                node_label = clickData["points"][0]["text"]
                print(f"Node {node_label} copied to clipboard")
                pyperclip.copy(node_label)
                return f"Node {node_label} copied to clipboard"
            return ""


def main():
    app = AlexNetTreeGraphApp()
    app.run()


if __name__ == "__main__":
    main()