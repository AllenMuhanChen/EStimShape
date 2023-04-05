from unittest import TestCase

import xmltodict

from src.mock.mock_tree_graph import fetch_tree_spec, parse_recursive_xml, recursive_tree_to_edges, MockTreeGraph, \
    MockTreeGraphApp
from src.tree_graph.tree_graph import TreeGraphApp

lineage_id = "1680721659342212"

class TestMockTreeGraph(TestCase):
    def test_app(self):
        app = MockTreeGraphApp()
        app.run()