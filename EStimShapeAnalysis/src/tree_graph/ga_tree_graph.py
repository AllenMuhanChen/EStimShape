from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from ast import literal_eval as make_tuple
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Any
from xml.etree import ElementTree as ET

import PIL
import xmltodict

from src.tree_graph.tree_graph import ColoredTreeGraph


class GATreeGraph(ColoredTreeGraph):
    def __init__(self, lineage_id: int, data_layer: TreeDataAccess):
        self.data_layer = data_layer

        # Get tree structure and convert to edges
        tree_spec = self.data_layer.get_tree_spec(lineage_id)
        edges = self._tree_to_edges(tree_spec)

        # Get stimulus IDs and responses
        self.stim_ids = [stim_id for edge in edges for stim_id in edge]
        y_values_for_stim_ids = self.data_layer.get_responses(self.stim_ids)

        # Get edge colors based on regimes
        edge_colors = self.data_layer.get_edge_colors(edges)

        super().__init__(y_values_for_stim_ids, edges, edge_colors, data_layer.image_base_path)
        self.highlighted_nodes = []

    def _tree_to_edges(self, tree: dict) -> List[Tuple[int, int]]:
        """Convert tree structure to list of edges"""
        edges = []
        if "children" in tree:
            for child in tree["children"]:
                edges.append((tree["identifier"], child["identifier"]))
                edges.extend(self._tree_to_edges(child))
        return edges



    def update_image_size(self, size: int):
        """Update size of node images"""
        for img in self.fig.layout.images:
            img.sizex = size
            img.sizey = size

        self.fig.data[0].update(marker_size=size / 4)
        return self.fig

    def highlight_nodes(self, nodes_to_highlight: List[int]):
        """Highlight selected nodes and their connections"""
        if not nodes_to_highlight:
            return self.reset_highlighted_nodes()

        # Get parent and children for highlighted nodes
        children_ids = self.data_layer.get_children_ids(nodes_to_highlight[0])

        # Get parent of parent unitl no more
        parent_id = self.data_layer.get_parent_id(nodes_to_highlight[0])
        all_parents = [parent_id]
        while parent_id != 0:
            parent_id = self.data_layer.get_parent_id(parent_id)
            if parent_id != 0:
                all_parents.append(parent_id)

        print(all_parents)



        # Update image opacities
        for img in self.fig.layout.images:
            try:
                img_id = int(img.name)
                if img_id in nodes_to_highlight:
                    img.opacity = 1.0
                elif img_id in children_ids:
                    img.opacity = 1.0
                elif img_id in all_parents:
                    #first gets 1.0, last gets 0.5, reduce opaqueness for in between
                    img.opacity = 1 - (all_parents.index(img_id) / len(all_parents) / 2)
                else:
                    img.opacity = 0.05
            except (ValueError, TypeError):
                continue



        self.fig.update_layout(images=self.fig.layout.images)

        # Specify Edge Opacities
        edge_opacities_for_nodes = {
            node: 1 for node in nodes_to_highlight
        }
        for i, parent in enumerate(all_parents):
            edge_opacities_for_nodes[parent] = 1 - (i / len(all_parents) / 2)
        for child in children_ids:
            edge_opacities_for_nodes[child] = 1

        # Update edge opacities
        for edge in self.fig.data[1:]:
            try:
                edge_nodes = make_tuple(edge.name)
                if edge_nodes[0] in edge_opacities_for_nodes.keys() and edge_nodes[1] in edge_opacities_for_nodes.keys():
                    opacity = min(edge_opacities_for_nodes[edge_nodes[0]], edge_opacities_for_nodes[edge_nodes[1]])
                    edge.update(opacity=opacity)
                else:
                    edge.update(opacity=0.05)
            except:
                continue

        self.highlighted_nodes = nodes_to_highlight
        return self.fig

    def reset_highlighted_nodes(self):
        """Reset all highlighting"""
        for img in self.fig.layout.images:
            img.opacity = 1
        self.fig.update_layout(images=self.fig.layout.images)

        for edge in self.fig.data[1:]:
            edge.update(opacity=1)
        self.highlighted_nodes = []
        return self.fig

    def _get_image(self, stim_id: int) -> PIL.Image.Image:
        """Get image for a stimulus ID"""
        image_path = self.data_layer.get_image_path(stim_id)
        if image_path and os.path.exists(image_path):
            return PIL.Image.open(image_path)
        return None


@dataclass
class TreeNode:
    identifier: int
    children: List['TreeNode']


class TreeDataAccess(ABC):
    @abstractmethod
    def get_tree_spec(self, lineage_id: int) -> dict:
        """Get and parse tree specification for a lineage"""
        pass

    @abstractmethod
    def get_responses(self, stim_ids: List[int]) -> Dict[int, float]:
        """Get response values for stimulus IDs"""
        pass

    @abstractmethod
    def get_parent_id(self, stim_id: int) -> Optional[int]:
        """Get parent ID for a stimulus"""
        pass

    @abstractmethod
    def get_children_ids(self, parent_id: int) -> List[int]:
        """Get child IDs for a parent stimulus"""
        pass

    @abstractmethod
    def get_regime(self, stim_id: int) -> str:
        """Get regime/type for a stimulus"""
        pass

    @abstractmethod
    def get_metadata(self, stim_id: int) -> Dict[str, Any]:
        """Get additional metadata for a stimulus"""
        pass

    @abstractmethod
    def get_all_lineages(self) -> List[int]:
        """Get all available lineage IDs"""
        pass

    @abstractmethod
    def get_edge_colors(self, edges: List[Tuple[int, int]]) -> Dict[Tuple[int, int], str]:
        """Get colors for edges based on regime types"""
        pass


class MySQLTreeDataAccess(TreeDataAccess):
    def __init__(self, conn, image_base_path: str):
        self.conn = conn
        self.image_base_path = image_base_path

    def get_tree_spec(self, lineage_id: int) -> dict:
        """Get and parse tree specification from LineageGaInfo"""
        self.conn.execute(
            "SELECT tree_spec from LineageGaInfo where lineage_id = %s ORDER BY gen_id DESC LIMIT 1",
            (lineage_id,)
        )
        tree_spec = self.conn.fetch_one()
        return self._parse_recursive_xml(tree_spec)

    def get_responses(self, stim_ids: List[int]) -> Dict[int, float]:
        """Get response values for multiple stimulus IDs"""
        responses = {}
        for stim_id in stim_ids:
            self.conn.execute(
                "SELECT response from StimGaInfo where stim_id = %s",
                (stim_id,)
            )
            response = self.conn.fetch_one()
            if response is not None:
                responses[stim_id] = float(response)
            else:
                responses[stim_id] = 0.0
                print(f"WARNING: stim with stim_id: {stim_id} has no response")
        return responses

    def get_parent_id(self, stim_id: int) -> Optional[int]:
        """Get parent ID for a stimulus"""
        self.conn.execute(
            "SELECT parent_id from StimGaInfo where stim_id = %s",
            (stim_id,)
        )
        return self.conn.fetch_one()

    def get_children_ids(self, parent_id: int) -> List[int]:
        """Get all child IDs for a parent stimulus"""
        self.conn.execute(
            "SELECT stim_id FROM StimGaInfo WHERE parent_id = %s",
            (parent_id,)
        )
        children_ids = [row[0] for row in self.conn.fetch_all()]
        return children_ids

    def get_regime(self, stim_id: int) -> str:
        """Get regime/type for a stimulus"""
        self.conn.execute(
            "SELECT stim_type from StimGaInfo where stim_id = %s",
            (stim_id,)
        )
        return self.conn.fetch_one()

    def get_metadata(self, stim_id: int) -> Dict[str, Any]:
        """Get combined metadata including components and shaft data"""
        metadata = {}

        # Get spec data
        self.conn.execute(
            "SELECT data from StimSpec where id = %s",
            (stim_id,)
        )
        spec_data = self.conn.fetch_one()

        if spec_data:
            try:
                spec_dict = xmltodict.parse(spec_data)
                allen_data = spec_dict.get("AllenMStickData", {})

                # Extract components to preserve
                metadata["components_to_preserve"] = allen_data.get("componentsToPreserve")

                # Extract components exploring
                metadata["components_exploring"] = allen_data.get("componentsExploring")

                # Extract shaft data
                metadata["shaft_data"] = allen_data.get("shaftData", {}).get("ShaftData")
            except Exception as e:
                print(f"Error parsing metadata for stim_id {stim_id}: {e}")

        return metadata

    def get_all_lineages(self) -> List[int]:
        """Get all available lineage IDs ordered by specific criteria"""
        query = """
        SELECT LineageGaInfo.lineage_id
        FROM (
            SELECT lineage_id, MAX(gen_id) as max_gen_id
            FROM LineageGaInfo
            GROUP BY lineage_id
        ) AS unique_lineages
        JOIN LineageGaInfo ON LineageGaInfo.lineage_id = unique_lineages.lineage_id 
            AND LineageGaInfo.gen_id = unique_lineages.max_gen_id
        WHERE LineageGaInfo.regime > 0
        ORDER BY LineageGaInfo.gen_id DESC, LineageGaInfo.regime DESC, 
                 LENGTH(LineageGaInfo.tree_spec) DESC
        LIMIT 10
        """
        self.conn.execute(query)
        return [row[0] for row in self.conn.fetch_all()]

    def get_image_path(self, stim_id: int) -> Optional[str]:
        """Get the image path for a stimulus ID"""
        for filename in os.listdir(self.image_base_path):
            if filename.startswith(str(stim_id)) and filename.endswith('compmap.png'):
                return os.path.join(self.image_base_path, filename)
        return None

    def get_edge_colors(self, edges: List[Tuple[int, int]]) -> Dict[Tuple[int, int], str]:
        """Get colors for edges based on monkey GA regime types"""
        colors_for_regimes = {
            "REGIME_ZERO": "black",
            "REGIME_ZERO_2D": "black",
            "REGIME_ONE": "red",
            "REGIME_ONE_2D": "red",
            "REGIME_TWO": "blue",
            "REGIME_TWO_2D": "blue",
            "REGIME_THREE": "green",
            "REGIME_THREE_2D": "green",
            "REGIME_FOUR": "yellow",
            "REGIME_FOUR_2D": "yellow",
        }

        edge_colors = {}
        for edge in edges:
            regime = self.get_regime(edge[1])
            if re.match(r"Zooming_\d+", regime):
                color = "orange"
            else:
                color = colors_for_regimes.get(regime, "default_color")
            edge_colors[edge] = color

        return edge_colors

    def _parse_recursive_xml(self, xml_string: str) -> dict:
        """Parse XML tree spec into dictionary structure"""
        root = ET.fromstring(xml_string)
        return self._parse_recursive_node(root)

    def _parse_recursive_node(self, elem: ET.Element) -> dict:
        """Recursively parse XML node into dictionary structure"""
        children = []
        for child_elem in elem.findall('Node'):
            children.append(self._parse_recursive_node(child_elem))

        return {
            "identifier": int(elem.text),
            "children": children
        }
