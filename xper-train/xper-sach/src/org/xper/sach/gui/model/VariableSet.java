package org.xper.sach.gui.model;

import java.util.TreeSet;

public class VariableSet {
	String name;
	TreeSet<String> variables;
	public VariableSet(String name, TreeSet<String> variables) {
		super();
		this.name = name;
		this.variables = variables;
	}
	public String getName() {
		return name;
	}
	public void setName(String name) {
		this.name = name;
	}
	public TreeSet<String> getVariables() {
		return variables;
	}
	public void setVariables(TreeSet<String> variables) {
		this.variables = variables;
	}
}
