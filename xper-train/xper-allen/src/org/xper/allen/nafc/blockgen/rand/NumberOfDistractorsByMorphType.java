package org.xper.allen.nafc.blockgen.rand;

public class NumberOfDistractorsByMorphType {
	private int numQMDistractors;
	private int numRandDistractors;


	public NumberOfDistractorsByMorphType() {
	}

	public int getNumQMDistractors() {
		return numQMDistractors;
	}

	public NumberOfDistractorsByMorphType(int numQMDistractors, int numRandDistractors) {
		super();
		this.numQMDistractors = numQMDistractors;
		this.numRandDistractors = numRandDistractors;
	}

	public void setNumQMDistractors(int numQMDistractors) {
		this.numQMDistractors = numQMDistractors;
	}

	public int getNumRandDistractors() {
		return numRandDistractors;
	}

	public void setNumRandDistractors(int numRandDistractors) {
		this.numRandDistractors = numRandDistractors;
	}

	public int getTotalNumDistractors() {
		return numQMDistractors + numRandDistractors;
	}
}