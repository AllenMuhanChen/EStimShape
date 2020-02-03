package org.xper.allen.specs;

import com.thoughtworks.xstream.XStream;

public class GaussSpec {
	double xCenter;
	double yCenter;
	double orientation;
	double frequency;
	double phase;
	double size;
	boolean animation;
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", GaussSpec.class);
		s.useAttributeFor("animation", boolean.class);
	}
	
	public String toXml () {
		return GaussSpec.toXml(this);
	}
	
	public static String toXml (GaussSpec spec) {
		return s.toXML(spec);
	}
	
	public static GaussSpec fromXml (String xml) {
		GaussSpec g = (GaussSpec)s.fromXML(xml);
		return g;
	}
	
	public GaussSpec() {}
	
	public GaussSpec(GaussSpec d) {
		xCenter = d.getXCenter();
		yCenter = d.getYCenter();
		orientation = d.getOrientation();
		frequency = d.getFrequency();
		phase = d.getPhase();
		size = d.getSize();
		animation = d.isAnimation();
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
	public double getOrientation() {
		return orientation;
	}
	public void setOrientation(double orientation) {
		this.orientation = orientation;
	}
	public double getFrequency() {
		return frequency;
	}
	public void setFrequency(double frequency) {
		this.frequency = frequency;
	}
	public double getPhase() {
		return phase;
	}
	public void setPhase(double phase) {
		this.phase = phase;
	}
	public double getSize() {
		return size;
	}
	public void setSize(double size) {
		this.size = size;
	}

	public boolean isAnimation() {
		return animation;
	}

	public void setAnimation(boolean animation) {
		this.animation = animation;
	}
}
