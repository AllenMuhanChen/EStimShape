from unittest import TestCase

from src.pga.app.run_tree_graph_app import GATreeGraphApp
from src.tree_graph.ga_tree_graph import recursive_tree_to_edges, _parse_recursive_xml

lineage_id = "1680721659342212"

class TestMockTreeGraph(TestCase):
    def test_app(self):
        app = GATreeGraphApp()
        app.run()


import unittest


class TestXMLParsing(unittest.TestCase):
    def test_parse_recursive_xml(self):
        xml_string = '<Node>1<Node>2</Node><Node>3<Node>4</Node></Node></Node>'
        expected_tree = {
            'identifier': 1,
            'children': [
                {'identifier': 2, 'children': []},
                {'identifier': 3, 'children': [{'identifier': 4, 'children': []}]}
            ]
        }
        result = _parse_recursive_xml(xml_string)
        self.assertEqual(result, expected_tree)

    def test_recursive_tree_to_edges(self):
        tree = {
            'identifier': 1,
            'children': [
                {'identifier': 2, 'children': []},
                {'identifier': 3, 'children': [{'identifier': 4, 'children': []}]}
            ]
        }
        expected_edges = [
            (1, 2),
            (1, 3),
            (3, 4)
        ]
        result = recursive_tree_to_edges(tree)
        self.assertEqual(result, expected_edges)

if __name__ == '__main__':
    unittest.main()
