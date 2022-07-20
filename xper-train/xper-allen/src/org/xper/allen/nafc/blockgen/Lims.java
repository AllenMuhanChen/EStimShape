package org.xper.allen.nafc.blockgen;

public class Lims {
	private double lowerLim;
	private double upperLim;

	public Lims(double lowerLim, double upperLim) {
		this.lowerLim = lowerLim;
		this.upperLim = upperLim;
	}

    public Lims() {

    }

	public double getLowerLim() {
		return lowerLim;
	}

	public void setLowerLim(double lowerLim) {
		this.lowerLim = lowerLim;
	}

	public double getUpperLim() {
		return upperLim;
	}

	public void setUpperLim(double upperLim) {
		this.upperLim = upperLim;
	}
}