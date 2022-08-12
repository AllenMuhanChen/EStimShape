package org.xper.eye.vo;

import org.xper.drawing.Coordinates2D;

public class EyeDeviceReading {
	Coordinates2D volt;

	Coordinates2D degree;

	public EyeDeviceReading() {
		volt = new Coordinates2D();
		degree = new Coordinates2D();
	}

	public EyeDeviceReading(Coordinates2D volt, Coordinates2D degree) {
		super();
		this.volt = volt;
		this.degree = degree;
	}

	public Coordinates2D getDegree() {
		return degree;
	}

	public void setDegree(Coordinates2D degree) {
		this.degree = degree;
	}

	public Coordinates2D getVolt() {
		return volt;
	}

	public void setVolt(Coordinates2D volt) {
		this.volt = volt;
	}

}
