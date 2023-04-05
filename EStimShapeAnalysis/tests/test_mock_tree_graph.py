from unittest import TestCase

import xmltodict

from src.mock.mock_tree_graph import fetch_tree_spec, parse_recursive_xml, recursive_tree_to_edges, MockTreeGraph
from src.tree_graph.tree_graph import TreeGraphApp

lineage_id = "1680721659342212"

class TestMockTreeGraph(TestCase):
    def test_app(self):
        mtg = MockTreeGraph(lineage_id)
        app = TreeGraphApp(mtg)
        app.run()