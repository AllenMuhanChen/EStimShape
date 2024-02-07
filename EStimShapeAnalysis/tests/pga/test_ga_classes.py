import unittest
from src.pga.ga_classes import Node  # replace with the actual import

class TestNode(unittest.TestCase):
    def setUp(self):
        self.node = Node('root')
        self.child1 = Node('child1')
        self.child2 = Node('child2')
        self.node.add_child(self.child1)
        self.node.add_child(self.child2)

    def test_add_and_find_child(self):
        self.node.add_child_to('root', Node('child3'))
        found_node = self.node.find('child3')
        self.assertIsNotNone(found_node)
        self.assertEqual(found_node.data, 'child3')

    def test_to_and_from_xml(self):
        xml_str = self.node.to_xml()
        print(xml_str)
        restored_node = Node.from_xml(xml_str)
        self.assertEqual(restored_node.data, self.node.data)
        self.assertEqual(len(restored_node.children), len(self.node.children))
        for restored_child, original_child in zip(restored_node.children, self.node.children):
            self.assertEqual(restored_child.data, original_child.data)


if __name__ == '__main__':
    unittest.main()
