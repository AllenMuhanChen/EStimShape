package org.xper.allen.specs;

import java.awt.*;
import java.util.Objects;

import org.xper.rfplot.drawing.png.ImageDimensions;

import com.thoughtworks.xstream.XStream;

public class NoisyPngSpec {
	double xCenter;
	double yCenter;
	ImageDimensions dimensions;
	String pngPath;
	String noiseMapPath;
	double alpha = 1;
	Color color;
	double noiseRate = 1;
	double noiseChance = 0; //doesn't impact actual drawing of noise, it's in here so we can change the reward rate based on noiseChance

	@Override
	public boolean equals(Object o) {
		if (this == o) return true;
		if (o == null || getClass() != o.getClass()) return false;
		NoisyPngSpec that = (NoisyPngSpec) o;
		return Double.compare(that.getxCenter(), getxCenter()) == 0 && Double.compare(that.getyCenter(), getyCenter()) == 0 && Double.compare(that.getAlpha(), getAlpha()) == 0 && getDimensions().equals(that.getDimensions()) && getPngPath().equals(that.getPngPath()) && getNoiseMapPath().equals(that.getNoiseMapPath());
	}

	@Override
	public int hashCode() {
		return Objects.hash(getxCenter(), getyCenter(), getDimensions(), getPngPath(), getNoiseMapPath(), getAlpha());
	}

	/**
	 * For specifying static noiseMap
	 */
	public NoisyPngSpec(double xCenter, double yCenter, ImageDimensions dimensions, String pngPath, String noiseMapPath, Color color, double noiseRate, double noiseChance) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.pngPath = pngPath;
		this.noiseMapPath = noiseMapPath;
		this.color = color;
		this.noiseRate = noiseRate;
		this.noiseChance = noiseChance;
    }

	/**
	 * NoiseMap and Color is specified
	 */
	public NoisyPngSpec(double xCenter, double yCenter, ImageDimensions dimensions, String path, String noiseMapPath, Color color) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.pngPath = path;
		this.noiseMapPath = noiseMapPath;
        this.color = color;
	}

	/**
	 * NoiseMap is specified
	 */
	public NoisyPngSpec(double xCenter, double yCenter, ImageDimensions dimensions, String path, String noiseMapPath) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.pngPath = path;
		this.noiseMapPath = noiseMapPath;
        this.color = Color.WHITE;
	}

	/**
	 * For generation where noiseMap is not specified.
	 * @param xCenter
	 * @param yCenter
	 * @param dimensions
	 * @param path
	 */
	public NoisyPngSpec(double xCenter, double yCenter, ImageDimensions dimensions, String path) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.pngPath = path;
        this.noiseMapPath = "";
		this.color = Color.WHITE;
	}

	public NoisyPngSpec() {

	}

	transient static XStream s;
	boolean animation = true;

	static {
		s = new XStream();
		s.alias("StimSpec", NoisyPngSpec.class);
		s.useAttributeFor("animation", boolean.class);
	}

	public String toXml () {
		return s.toXML(this);
	}

	public static NoisyPngSpec fromXml (String xml) {
		NoisyPngSpec p = (NoisyPngSpec)s.fromXML(xml);
		return p;
	}

	public double getxCenter() {
		return xCenter;
	}

	public void setxCenter(double xCenter) {
		this.xCenter = xCenter;
	}

	public double getyCenter() {
		return yCenter;
	}

	public void setyCenter(double yCenter) {
		this.yCenter = yCenter;
	}

	public String getPath() {
		return pngPath;
	}

	public void setPngPath(String path) {
		this.pngPath = path;
	}
	public ImageDimensions getImageDimensions() {
		return dimensions;
	}
	public void setImageDimensions(ImageDimensions dimensions) {
		this.dimensions = dimensions;
	}
	public ImageDimensions getDimensions() {
		return dimensions;
	}
	public void setDimensions(ImageDimensions dimensions) {
		this.dimensions = dimensions;
	}

	public double getAlpha() {
		return alpha;
	}

	public String getPngPath() {
		return pngPath;
	}

	public String getNoiseMapPath() {
		return noiseMapPath;
	}

	public void setNoiseMapPath(String noiseMapPath) {
		this.noiseMapPath = noiseMapPath;
	}

	public Color getColor() {
		return color;
	}

	public void setColor(Color color) {
		this.color = color;
	}

	public double getNoiseRate() {
		return noiseRate;
	}

	public double getNoiseChance() {
		return noiseChance;
	}
}