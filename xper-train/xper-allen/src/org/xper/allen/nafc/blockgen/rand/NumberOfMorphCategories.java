package org.xper.allen.nafc.blockgen.rand;

public class NumberOfMorphCategories {
	private int numMMCategories;
	private int numQMCategories;

	public NumberOfMorphCategories(int numMMCategories, int numQMCategories) {
		super();
		this.numMMCategories = numMMCategories;
		this.numQMCategories = numQMCategories;
	}
	
	public NumberOfMorphCategories() {
	}

	public int getNumMMCategories() {
		return numMMCategories;
	}

	public void setNumMMCategories(int numMMCategories) {
		this.numMMCategories = numMMCategories;
	}

	public int getNumQMCategories() {
		return numQMCategories;
	}

	public void setNumQMCategories(int numQMCategories) {
		this.numQMCategories = numQMCategories;
	}

}