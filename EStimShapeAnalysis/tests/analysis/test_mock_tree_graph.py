from unittest import TestCase

from analysis.ga.oldmockga.mock_tree_graph import _parse_recursive_xml, recursive_tree_to_edges, MockTreeGraphApp

lineage_id = "1680721659342212"

class TestMockTreeGraph(TestCase):
    def test_app(self):
        app = MockTreeGraphApp()
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
