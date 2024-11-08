from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Tuple
from src.tree_graph.ga_tree_graph import TreeDataAccess


class AlexNetDataAccess(TreeDataAccess):
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
        return [row[0] for row in self.conn.fetch_all()]

    def get_regime(self, stim_id: int) -> str:
        """Get regime/type for a stimulus"""
        self.conn.execute(
            "SELECT stim_type from StimGaInfo where stim_id = %s",
            (stim_id,)
        )
        return self.conn.fetch_one()

    def get_metadata(self, stim_id: int) -> Dict[str, Any]:
        """Get metadata - for AlexNet GA, this includes activation values"""
        metadata = {}

        # Get activation value
        self.conn.execute(
            "SELECT activation FROM UnitActivations WHERE stim_id = %s",
            (stim_id,)
        )
        activation = self.conn.fetch_one()
        if activation:
            metadata["activation"] = float(activation)

        # Get mutation magnitude
        self.conn.execute(
            "SELECT mutation_magnitude FROM StimGaInfo WHERE stim_id = %s",
            (stim_id,)
        )
        magnitude = self.conn.fetch_one()
        if magnitude:
            metadata["mutation_magnitude"] = float(magnitude)

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
        ORDER BY LineageGaInfo.gen_id DESC, LENGTH(LineageGaInfo.tree_spec) DESC
        LIMIT 10
        """
        self.conn.execute(query)
        return [row[0] for row in self.conn.fetch_all()]

    def get_image_path(self, stim_id: int) -> Optional[str]:
        """Get the image path for a stimulus ID"""
        for filename in os.listdir(self.image_base_path):
            if filename.startswith(str(stim_id)) and filename.endswith('.png'):
                return os.path.join(self.image_base_path, filename)
        return None

    def get_edge_colors(self, edges: List[Tuple[int, int]]) -> Dict[Tuple[int, int], str]:
        """Get colors for edges based on AlexNet GA regime types"""
        colors_for_regimes = {
            "SEEDING": "black",
            "RF_LOCATE": "red",
            "GROWING": "blue"
        }

        edge_colors = {}
        for edge in edges:
            regime = self.get_regime(edge[1])
            edge_colors[edge] = colors_for_regimes.get(regime, "gray")
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