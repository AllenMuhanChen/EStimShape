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
}