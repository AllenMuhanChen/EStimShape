package org.xper.eye.mapping;

import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;


/**
 * X, Y: eye position in degree
 * H, V: reading of the Iscan in volt
 *
 * V - V0 = Y * Syv + X * Sxv
 * H - H0 = Y * Syh + X * Sxh
 *
 * =>
 *
 * Y = ((V - V0)* Sxh - (H -H0) * Sxv) / (Syv * Sxh - Syh * Sxv)
 * X = ((H - H0) - Y * Syh) / Sxh
 *
 * */

public class LinearMappingAlgorithm implements MappingAlgorithm {
	@Dependency
	double Syv;
	@Dependency
	double Sxv;
	@Dependency
	double Syh;
	@Dependency
	double Sxh;

	public Coordinates2D degree2Volt(Coordinates2D degree, Coordinates2D eyeZero) {
		Coordinates2D volt = new Coordinates2D();
		volt.setY(degree.getY() * Syv + degree.getX() * Sxv + eyeZero.getY());
		volt.setX(degree.getY() * Syh + degree.getX() * Sxh + eyeZero.getX());
		return volt;
	}

	public Coordinates2D volt2Degree(Coordinates2D volt, Coordinates2D eyeZero) {
		Coordinates2D degree = new Coordinates2D();
		degree.setY(((volt.getY() - eyeZero.getY()) * Sxh - (volt.getX() - eyeZero.getX()) * Sxv) / (Syv * Sxh - Syh * Sxv));
		degree.setX(((volt.getX() - eyeZero.getX()) - volt.getY() * Syh) / Sxh);
		if (degree.getY() > 90) degree.setY(90);
		if (degree.getX() > 90) degree.setX(90);
		return degree;
	}

	public double getSyv() {
		return Syv;
	}

	public void setSyv(double syv) {
		Syv = syv;
	}

	public double getSxv() {
		return Sxv;
	}

	public void setSxv(double sxv) {
		Sxv = sxv;
	}

	public double getSyh() {
		return Syh;
	}

	public void setSyh(double syh) {
		Syh = syh;
	}

	public double getSxh() {
		return Sxh;
	}

	public void setSxh(double sxh) {
		Sxh = sxh;
	}
}
