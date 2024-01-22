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
	double numNoiseFrames = -1; // -1 means entire stimulus duration

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

	public static NoisyPngSpec createStaticSpec(double xCenter, double yCenter, ImageDimensions dimensions, String pngPath, String noiseMapPath, Color color) {
		return new NoisyPngSpec(xCenter, yCenter, dimensions, pngPath, noiseMapPath,  color, 1);
	}

	/**
	 * For specifying static noiseMap
	 */
	public NoisyPngSpec(double xCenter, double yCenter, ImageDimensions dimensions, String pngPath, String noiseMapPath, Color color, double numNoiseFrames) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.pngPath = pngPath;
		this.noiseMapPath = noiseMapPath;
		this.color = color;
		this.numNoiseFrames = numNoiseFrames;
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
//		System.out.println(xml);
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

	public void setAlpha(double alpha) {
		this.alpha = alpha;
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

	public double getNumNoiseFrames() {
		return numNoiseFrames;
	}
	public void setNumNoiseFrames(double numNoiseFrames) {
		this.numNoiseFrames = numNoiseFrames;
	}
}