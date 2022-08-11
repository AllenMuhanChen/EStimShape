package org.xper.sach.gui.view;

import java.awt.Component;

import javax.swing.ImageIcon;
import javax.swing.JTree;
import javax.swing.tree.DefaultTreeCellRenderer;
import javax.swing.tree.TreeCellRenderer;

public class VariableSetCellRenderer extends DefaultTreeCellRenderer implements TreeCellRenderer {
	private static final long serialVersionUID = -7832496775819645991L;
	ImageIcon closeIcon = new ImageIcon(this.getClass().getResource("images/variable_set_closed.gif"));
	ImageIcon openIcon = new ImageIcon(this.getClass().getResource("images/variable_set_open.gif"));

	public Component getTreeCellRendererComponent(JTree tree, Object value,
			boolean selected, boolean expanded, boolean leaf, int row,
			boolean hasFocus) {
		super.getTreeCellRendererComponent(tree, value, selected, expanded, leaf, row, hasFocus);
		if (leaf) {
	        if (selected) {
	        	setIcon(openIcon);
	        } else {
	        	setIcon(closeIcon);
	        }
		}
		return this;
	}

}
