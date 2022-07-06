package org.xper.allen.nafc.blockgen;

public class DistanceLims {
	private double distanceLowerLim;
	private double distanceUpperLim;

	public DistanceLims(double distanceLowerLim, double distanceUpperLim) {
		this.distanceLowerLim = distanceLowerLim;
		this.distanceUpperLim = distanceUpperLim;
	}

	public double getDistanceLowerLim() {
		return distanceLowerLim;
	}

	public void setDistanceLowerLim(double distanceLowerLim) {
		this.distanceLowerLim = distanceLowerLim;
	}

	public double getDistanceUpperLim() {
		return distanceUpperLim;
	}

	public void setDistanceUpperLim(double distanceUpperLim) {
		this.distanceUpperLim = distanceUpperLim;
	}
}