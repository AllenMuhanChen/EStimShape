package org.xper.allen.specs;

import com.thoughtworks.xstream.XStream;

public class PngSpec {
	double xCenter;
	double yCenter;
	String path;
	
	public PngSpec(double xCenter, double yCenter, String path) {
		this.xCenter = xCenter;
		this.yCenter = yCenter;
		this.path = path;
	}
	public PngSpec() {

	}
	
	transient static XStream s;
	
	static {
		s = new XStream();
		//s.alias("StimSpec", PngSpec.class);
	}
	
	public String toXml () {
		return s.toXML(this);
	}
	
	public static PngSpec fromXml (String xml) {
		System.out.println(xml);
		PngSpec p = (PngSpec)s.fromXML(xml);
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
	
	
}
