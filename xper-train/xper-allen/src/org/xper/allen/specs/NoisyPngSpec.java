package org.xper.allen.specs;

import java.awt.Dimension;

import org.xper.allen.drawing.png.ImageDimensions;

import com.thoughtworks.xstream.XStream;

public class NoisyPngSpec {
	double xCenter;
	double yCenter;
	ImageDimensions dimensions;
	String pngPath;
	String noiseMapPath;
	double alpha = 1;
	
	/**
	 * NoiseMap is specified
	 */
	public NoisyPngSpec(double xCenter, double yCenter, ImageDimensions dimensions, String path, String noiseMapPath) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.pngPath = path;
		this.noiseMapPath = path;
		this.alpha = 1;
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
		this.alpha = 1;
		this.noiseMapPath = "";
	}
	
	public NoisyPngSpec() {

	}
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", PngSpec.class);
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

	public void setPngPath(String pngPath) {
		this.pngPath = pngPath;
	}

	public String getNoiseMapPath() {
		return noiseMapPath;
	}

	public void setNoiseMapPath(String noiseMapPath) {
		this.noiseMapPath = noiseMapPath;
	}
	
}
