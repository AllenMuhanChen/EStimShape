package org.xper.allen.app.fixation;

import org.xper.rfplot.drawing.png.ImageDimensions;

import com.thoughtworks.xstream.XStream;

public class PngStimSpec {
	double xCenter;
	double yCenter;
	ImageDimensions dimensions;
	String path;
	double alpha = 1;
	
	/**
	 * For generation where alpha is specified. 
	 * @param xCenter
	 * @param yCenter
	 * @param dimensions
	 * @param path
	 * @param alpha
	 */
	public PngStimSpec(double xCenter, double yCenter, ImageDimensions dimensions, String path, double alpha) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.path = path;
		this.alpha = alpha;
	}
	
	/**
	 * For generation where alpha is not specified: set to 1. 
	 * @param xCenter
	 * @param yCenter
	 * @param dimensions
	 * @param path
	 */
	public PngStimSpec(double xCenter, double yCenter, ImageDimensions dimensions, String path) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.dimensions = dimensions;
		this.path = path;
		this.alpha = 1;
	}
	
	public PngStimSpec() {

	}
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", PngStimSpec.class);
	}
	
	public String toXml () {
		return s.toXML(this);
	}
	
	public static PngStimSpec fromXml (String xml) {
		System.out.println(xml);
		PngStimSpec p = (PngStimSpec)s.fromXML(xml);
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
		return path;
	}

	public void setPath(String path) {
		this.path = path;
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
	
}
