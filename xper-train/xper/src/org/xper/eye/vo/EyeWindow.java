package org.xper.eye.vo;

import org.xper.drawing.Coordinates2D;

public class EyeWindow {
	Coordinates2D center;
	double size;
	public EyeWindow() {
		center = new Coordinates2D();
	}
	public EyeWindow(Coordinates2D center, double size) {
		super();
		this.center = center;
		this.size = size;
	}
	public Coordinates2D getCenter() {
		return center;
	}
	public void setCenter(Coordinates2D center) {
		this.center = center;
	}
	public double getSize() {
		return size;
	}
	public void setSize(double size) {
		this.size = size;
	}
}
