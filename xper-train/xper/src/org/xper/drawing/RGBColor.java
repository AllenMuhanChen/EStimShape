package org.xper.drawing;

import java.util.Objects;

public class RGBColor {
	float red;

	float green;

	float blue;

	public RGBColor(float red, float green, float blue) {
		super();
		this.red = red;
		this.green = green;
		this.blue = blue;
	}

	public RGBColor(double red, double green, double blue) {
		super();
		this.red = (float) red;
		this.green = (float) green;
		this.blue = (float) blue;
	}


	public RGBColor(RGBColor other) {
		this.red = other.red;
		this.green = other.green;
		this.blue = other.blue;
	}

	public RGBColor(double[] rgb){
		super();
		this.red = (float) rgb[0];
		this.green = (float) rgb[1];
		this.blue = (float) rgb[2];
	}

	public float getBlue() {
		return blue;
	}

	public void setBlue(float blue) {
		this.blue = blue;
	}

	public float getGreen() {
		return green;
	}

	public void setGreen(float green) {
		this.green = green;
	}

	public float getRed() {
		return red;
	}

	public void setRed(float red) {
		this.red = red;
	}

	public RGBColor() {
	}

	@Override
	public boolean equals(Object o) {
		if (this == o) return true;
		if (o == null || getClass() != o.getClass()) return false;
		RGBColor rgbColor = (RGBColor) o;
		return Float.compare(getRed(), rgbColor.getRed()) == 0 && Float.compare(getGreen(), rgbColor.getGreen()) == 0 && Float.compare(getBlue(), rgbColor.getBlue()) == 0;
	}

	@Override
	public int hashCode() {
		return Objects.hash(getRed(), getGreen(), getBlue());
	}

	@Override
	public String toString() {
		return "RGBColor{" +
				"red=" + red +
				", green=" + green +
				", blue=" + blue +
				'}';
	}
}