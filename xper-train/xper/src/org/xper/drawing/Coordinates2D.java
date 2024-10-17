package org.xper.drawing;

import java.util.Objects;

public class Coordinates2D implements Cloneable {
	double x;
	double y;

	public double getX() {
		return x;
	}
	public void setX(double x) {
		this.x = x;
	}
	public double getY() {
		return y;
	}
	public void setY(double y) {
		this.y = y;
	}
	public Coordinates2D(double x, double y) {
		super();
		this.x = x;
		this.y = y;
	}

	@Override
	public boolean equals(Object o) {
		if (this == o) return true;
		if (o == null || getClass() != o.getClass()) return false;
		Coordinates2D that = (Coordinates2D) o;
		return Double.compare(that.getX(), getX()) == 0 && Double.compare(that.getY(), getY()) == 0;
	}

	@Override
	public int hashCode() {
		return Objects.hash(getX(), getY());
	}

	public Coordinates2D() {
	}

	public String toString() {
		return "("+x+","+y+")";
	}

	public double distance(Coordinates2D point) {
		return Math.hypot(x-point.x, y-point.y);
	}

	public Coordinates2D clone() {
		return new Coordinates2D(x, y);
	}
}