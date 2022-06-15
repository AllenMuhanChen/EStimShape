package org.xper.allen.nafc.blockgen;

public class SampleDistance {
	private double sampleDistanceLowerLim;
	private double sampleDistanceUpperLim;

	public SampleDistance(double sampleDistanceLowerLim, double sampleDistanceUpperLim) {
		this.sampleDistanceLowerLim = sampleDistanceLowerLim;
		this.sampleDistanceUpperLim = sampleDistanceUpperLim;
	}

	public double getSampleDistanceLowerLim() {
		return sampleDistanceLowerLim;
	}

	public void setSampleDistanceLowerLim(double sampleDistanceLowerLim) {
		this.sampleDistanceLowerLim = sampleDistanceLowerLim;
	}

	public double getSampleDistanceUpperLim() {
		return sampleDistanceUpperLim;
	}

	public void setSampleDistanceUpperLim(double sampleDistanceUpperLim) {
		this.sampleDistanceUpperLim = sampleDistanceUpperLim;
	}
}