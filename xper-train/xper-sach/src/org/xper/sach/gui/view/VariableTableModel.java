package org.xper.sach.gui.view;

import java.util.ArrayList;
import java.util.List;

import javax.swing.tree.TreePath;

import org.jdesktop.swingx.treetable.DefaultMutableTreeTableNode;
import org.jdesktop.swingx.treetable.DefaultTreeTableModel;
import org.xper.db.vo.SystemVariable;
import org.xper.sach.gui.model.VariableSet;
import org.xper.sach.gui.model.XperLauncherModel;

public class VariableTableModel extends DefaultTreeTableModel {
	private static final long serialVersionUID = -492069424049177952L;
	
	String [] columnNames = {"Name", "Value"};
	List<String> visibleVariables = new ArrayList<String>();
	
	static final int NAME_COLUMN = 0;
	static final int VALUE_COLUMN = 1;
	
	XperLauncherModel model;
	
	public VariableTableModel(XperLauncherModel model) {
		super(new DefaultMutableTreeTableNode("Variables"));
		this.model = model;
	}
	
	public void update(VariableSet variableSet) {
		DefaultMutableTreeTableNode rootNode = (DefaultMutableTreeTableNode)getRoot();
		int nChild = rootNode.getChildCount();
		for (int i = nChild - 1; i >= 0; i --) {
			rootNode.remove(i);
		}
		if (variableSet != null) {
			visibleVariables = new ArrayList<String>(variableSet.getVariables());
			for (String name : visibleVariables) {
				DefaultMutableTreeTableNode node = new DefaultMutableTreeTableNode(name);
				rootNode.add(node);
				SystemVariable v = model.getAllVariables().get(name);
				for (int i = 0; i < v.getValues().size(); i ++) {
					node.add(new DefaultMutableTreeTableNode(String.valueOf(i)));
				}
			}
		} else {
			visibleVariables = new ArrayList<String>();
		}
		modelSupport.fireNewRoot();
	}
	
	public int getColumnCount() {
		return columnNames.length;
	}
	public Object getValueAt(Object node, int column) {	
		if (node == getRoot()) {
			return getRoot().getUserObject();
		}
		DefaultMutableTreeTableNode n = (DefaultMutableTreeTableNode)node;
		if (n.isLeaf()) {
			DefaultMutableTreeTableNode parent = (DefaultMutableTreeTableNode)n.getParent();
			String variableName = (String)parent.getUserObject();
			String index = (String)n.getUserObject();
			switch(column) {
			case NAME_COLUMN: 
				return index;
			case VALUE_COLUMN:
				return model.getAllVariables().get(variableName).getValue(Integer.parseInt(index));
			default: 
				return "";
			}
		} else {
			if (column == NAME_COLUMN) {
				return n.getUserObject();
			} else {
				return "";
			}
		}
	}
	
	@Override
	public void setValueAt(Object value, Object node, int column) {
		if (value == null || ((String)value).trim().length() == 0) {
		} else {
			DefaultMutableTreeTableNode n = (DefaultMutableTreeTableNode)node;
			if (n.isLeaf() && column == VALUE_COLUMN) {
				DefaultMutableTreeTableNode parent = (DefaultMutableTreeTableNode)n.getParent();
				String variableName = (String)parent.getUserObject();
				String index = (String)n.getUserObject();
				int ind = Integer.parseInt(index);
				model.writeSystemVar(variableName, ind, (String)value);
				model.getAllVariables().get(variableName).setValue(ind, (String)value);
				modelSupport.fireChildChanged(new TreePath(new Object[] {getRoot(), parent}), ind, node);
			}
		}
	}
	
	@Override
	public String getColumnName(int index) {
		return columnNames[index];
	}
	
	@Override
	public boolean isCellEditable(Object node, int column) {
		DefaultMutableTreeTableNode n = (DefaultMutableTreeTableNode)node;
		if (column == VALUE_COLUMN && node != getRoot() && node != null && n.isLeaf()) {
			return true;
		} else {
			return false;
		}
	}
	@Override
	public Class<?> getColumnClass(int index) {
		return String.class;
	}
	
}
