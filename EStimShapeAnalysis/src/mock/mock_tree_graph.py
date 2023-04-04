from __future__ import annotations
from src.tree_graph.tree_graph import TreeGraph
from src.util.connection import Connection

import xml.etree.ElementTree as ET

conn = Connection("allen_estimshape_dev_221110")


class MockTreeGraph(TreeGraph):
    def __init__(self, lineage_id):
        tree_spec = fetch_tree_spec(lineage_id)
        self.edges = recursive_tree_to_edges(tree_spec)
        self.stim_ids = {stim_id for edge in self.edges for stim_id in edge}
        self.y_values_for_stim_ids = fetch_responses_for(self.stim_ids)


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
