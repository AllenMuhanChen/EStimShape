package org.xper.allen.nafc.blockgen;

import java.util.LinkedList;
import java.util.List;

public class NumberOfDistractorsForPsychometricTrial {
	public int numPsychometricDistractors;
	public int numRandDistractors;
	public int numTotal;

	public NumberOfDistractorsForPsychometricTrial() {
	}

	public NumberOfDistractorsForPsychometricTrial(int numPsychometricDistractors, int numRandDistractors) {
		super();
		this.numPsychometricDistractors = numPsychometricDistractors;
		this.numRandDistractors = numRandDistractors;
		this.numTotal = numPsychometricDistractors + numRandDistractors;
	}

}