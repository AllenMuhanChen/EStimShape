package org.xper.allen.nafc.blockgen;

public class NumberOfDistractorsForPsychometricTrial {
	private int numPsychometricDistractors;
	private int numRandDistractors;
	public int numTotal;

	public NumberOfDistractorsForPsychometricTrial() {
	}

	public NumberOfDistractorsForPsychometricTrial(int numPsychometricDistractors, int numRandDistractors) {
		super();
		this.setNumPsychometricDistractors(numPsychometricDistractors);
		this.setNumRandDistractors(numRandDistractors);
		updateNumTotal();
	}

	private void updateNumTotal() {
		this.numTotal = this.getNumPsychometricDistractors() + this.getNumRandDistractors();
	}

	public int getNumPsychometricDistractors() {
		return numPsychometricDistractors;
	}

	public int getNumRandDistractors() {
		return numRandDistractors;
	}

	public void setNumPsychometricDistractors(int numPsychometricDistractors) {
		this.numPsychometricDistractors = numPsychometricDistractors;
		updateNumTotal();
	}

	public void setNumRandDistractors(int numRandDistractors) {
		this.numRandDistractors = numRandDistractors;
		updateNumTotal();
	}
}