package org.xper.allen.nafc.blockgen;

public class NumberOfDistractors {
	public int numPsychometricDistractors;
	public int numRandDistractors;
	public int numTotal;

	public NumberOfDistractors() {
	}


	public NumberOfDistractors(int numPsychometricDistractors, int numRandDistractors) {
		super();
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.numRandDistractors = numRandDistractors;
		this.numTotal = numPsychometricDistractors + numRandDistractors;
	}
}