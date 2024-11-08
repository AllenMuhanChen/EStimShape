from typing import Dict, List, Tuple

import networkx as nx
import os
from PIL import Image
import plotly.graph_objects as go


class TreeGraph:
    def __init__(self, y_values_for_stim_ids: Dict[int, float], edges: List[Tuple[int, int]], image_folder: str):
        self.edges = edges
        self.image_folder = image_folder
        self._create_tree_graph(y_values_for_stim_ids, edges)

    fig: go.Figure

    def _create_tree_graph(self, y_values_for_stim_ids, edges):
        self.node_size = 100

        tree = self._create_directed_graph(edges)
        self.tree = tree

        pos = self._compute_node_positions(tree, y_values_for_stim_ids)
        self.pos = pos

        layout = self._create_layout(pos, tree)

        self.fig = go.Figure(layout=layout)

        self.fig.add_traces(self._create_nodes(pos, tree))

        self.fig.add_traces(self._create_edges(pos, tree))

    def _create_directed_graph(self, edges):
        # Create a directed graph (tree)
        tree = nx.DiGraph()
        tree.add_edges_from(edges)
        return tree

    def _compute_node_positions(self, tree, y_values_for_stim_ids):
        # Compute the x positions using the 'dot' layout
        pos_x = nx.drawing.nx_agraph.graphviz_layout(tree, prog="dot")
        # Combine the x positions from pos_x and y positions from stim_id_y_positions
        pos = {node: (pos_x[node][0], y_values_for_stim_ids[node]) for node in tree.nodes()}
        return pos

    def _create_layout(self, pos, tree):
        layout = go.Layout(
            showlegend=False,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=True, ticks="outside"),
            yaxis_side="left",
            images=self._get_images_for_stims(),
            uirevision=True,
        )
        return layout

    def _create_nodes(self, pos, tree) -> go.Scatter | list[go.Scatter]:
        self.node_trace = go.Scatter(
            x=[pos[k][0] for k in tree.nodes()],
            y=[pos[k][1] for k in tree.nodes()],
            mode="markers+text",
            text=list(tree.nodes()),
            textposition="bottom center",
            marker=dict(size=self.node_size/4, color="lightblue"),
            hoverinfo="text",
            opacity=0
        )
        return self.node_trace

    def _create_edges(self, pos, tree) -> go.Scatter | list[go.Scatter]:
        edge_trace = go.Scatter(
            x=[x for edge in tree.edges() for x in (pos[edge[0]][0], pos[edge[1]][0], None)],
            y=[y for edge in tree.edges() for y in (pos[edge[0]][1], pos[edge[1]][1], None)],
            mode="lines",
            line=dict(color="black", width=2),
            hoverinfo="none",
        )
        return edge_trace

    def _get_images_for_stims(self):
        images = []
        for stim_id in self.tree.nodes():
            image = go.layout.Image(
                name=stim_id,
                source=self._get_image(stim_id),
                xref="x",
                yref="y",
                x=self.pos[stim_id][0],
                y=self.pos[stim_id][1],
                sizex=self.node_size,
                sizey=self.node_size,
                xanchor="center",
                yanchor="middle",
                sizing="contain",
                layer="above"
            )
            images.append(image)
        return images

    def _get_image(self, stim_id):
        img = Image.open(os.path.join(self.image_folder, f"{stim_id}.png"))
        return img


class ColoredTreeGraph(TreeGraph):
    def __init__(self, y_values_for_stim_ids: Dict[int, float], edges: List[Tuple[int, int]],
                 edge_colors: Dict[Tuple[int, int], str], image_folder: str):
        self.edge_colors = edge_colors
        super().__init__(y_values_for_stim_ids, edges, image_folder)

    def _create_edges(self, pos, tree) -> List[go.Scatter]:
        edge_traces = []
        for edge in tree.edges():
            x = [pos[edge[0]][0], pos[edge[1]][0], None]
            y = [pos[edge[0]][1], pos[edge[1]][1], None]
            color = self.edge_colors[edge]
            edge_trace = go.Scatter(
                name=str(edge),
                x=x,
                y=y,
                mode="lines",
                line=dict(width=2, color=color),
                hoverinfo="none",
            )
            edge_traces.append(edge_trace)
        return edge_traces