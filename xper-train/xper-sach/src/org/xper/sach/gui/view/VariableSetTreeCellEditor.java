package org.xper.sach.gui.view;

import java.util.EventObject;

import javax.swing.JTree;
import javax.swing.tree.DefaultTreeCellEditor;
import javax.swing.tree.DefaultTreeCellRenderer;
import javax.swing.tree.TreeCellEditor;
import javax.swing.tree.TreeNode;

public class VariableSetTreeCellEditor extends DefaultTreeCellEditor {

	public VariableSetTreeCellEditor(JTree tree, DefaultTreeCellRenderer renderer, TreeCellEditor editor) {
		super(tree, renderer, editor);
	}
	
	public VariableSetTreeCellEditor(JTree tree, DefaultTreeCellRenderer renderer) {
		super(tree, renderer);
	}

	@Override
	public boolean isCellEditable(EventObject event) {
		boolean returnValue = super.isCellEditable(event);
	    // If still possible, check if current tree node is a leaf
	    if (returnValue) {
	      Object node = tree.getLastSelectedPathComponent();
	      if ((node != null) && (node instanceof TreeNode)) {
	        TreeNode treeNode = (TreeNode) node;
	        returnValue = treeNode.isLeaf();
	      }
	    }
	    return returnValue;
	}
}
