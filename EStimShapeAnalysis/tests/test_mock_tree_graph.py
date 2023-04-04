from unittest import TestCase

import xmltodict

from src.mock.mock_tree_graph import fetch_tree_spec, parse_recursive_xml, recursive_tree_to_edges, MockTreeGraph
lineage_id = "1680642528217274"

class TestMockTreeGraph(TestCase):
    def test_fetch_tree_spec(self):
        tree_spec = fetch_tree_spec(lineage_id)
        print(tree_spec)
        edges = recursive_tree_to_edges(tree_spec)
        print(edges)

    def test_init(self):
        mtg = MockTreeGraph(lineage_id)
        print(mtg.stim_ids)
        print(mtg.y_values_for_stim_ids)
