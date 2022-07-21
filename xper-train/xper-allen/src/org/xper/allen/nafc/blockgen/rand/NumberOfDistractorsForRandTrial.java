package org.xper.allen.nafc.blockgen.rand;

public class NumberOfDistractorsForRandTrial {
	private int numQMDistractors;
	private int numRandDistractors;
	private int numTotal;

	public NumberOfDistractorsForRandTrial() {
	}

	public int getNumQMDistractors() {
		return numQMDistractors;
	}

	public NumberOfDistractorsForRandTrial(int numQMDistractors, int numRandDistractors) {
		super();
		this.numQMDistractors = numQMDistractors;
		this.numRandDistractors = numRandDistractors;
		updateNumTotal();
	}

	public void setNumQMDistractors(int numQMDistractors) {
		this.numQMDistractors = numQMDistractors;
		updateNumTotal();
	}

	public int getNumRandDistractors() {
		return numRandDistractors;
	}

	public void setNumRandDistractors(int numRandDistractors) {
		this.numRandDistractors = numRandDistractors;
		updateNumTotal();
	}

	public int getTotalNumDistractors() {
		return numQMDistractors + numRandDistractors;
	}

	private void updateNumTotal(){
		this.numTotal = numQMDistractors + numRandDistractors;
	}

	public int getNumTotal() {
		return numTotal;
	}
}