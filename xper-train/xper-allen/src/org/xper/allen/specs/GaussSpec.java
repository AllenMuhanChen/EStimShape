package org.xper.allen.specs;

import com.thoughtworks.xstream.XStream;

public class GaussSpec {
	double xCenter;
	double yCenter;
	double size;
	double brightness;
	
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", GaussSpec.class);
		s.useAttributeFor("animation", boolean.class);
	}
	
	public String toXml () {
		return s.toXML(this);
	}

	public static GaussSpec fromXml (String xml) {
		GaussSpec g = (GaussSpec)s.fromXML(xml);
		return g;
	}
	
	public GaussSpec() {}
	
	public GaussSpec(double xCenter, double yCenter, double size, double brightness) {
		super();
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.size = size;
		this.brightness = brightness;
	}

	public double getXCenter() {
		return xCenter;
	}
	public void setXCenter(double center) {
		xCenter = center;
	}
	public double getYCenter() {
		return yCenter;
	}
	public void setYCenter(double center) {
		yCenter = center;
	}

	public double getSize() {
		return size;
	}
	public void setSize(double size) {
		this.size = size;
	}

	public double getBrightness() {
		return brightness;
	}

	public void setBrightness(double brightness) {
		this.brightness = brightness;
	}



}
