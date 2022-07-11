package org.xper.allen.nafc.blockgen;

public class Lims {
	private double lowerLim;
	private double upperLim;

	public Lims(double distanceLowerLim, double distanceUpperLim) {
		this.lowerLim = distanceLowerLim;
		this.upperLim = distanceUpperLim;
	}

	public double getLowerLim() {
		return lowerLim;
	}

	public void setLowerLim(double distanceLowerLim) {
		this.lowerLim = distanceLowerLim;
	}

	public double getUpperLim() {
		return upperLim;
	}

	public void setUpperLim(double distanceUpperLim) {
		this.upperLim = distanceUpperLim;
	}
}