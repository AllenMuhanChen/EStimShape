package org.xper.rfplot.drawing;

import com.thoughtworks.xstream.XStream;
import org.xper.rfplot.XMLizable;

public class GaborSpec implements XMLizable {
	double xCenter;
	double yCenter;
	double orientation;
	double frequency;
	double phase;
	double size;
	boolean animation;

	protected transient static XStream s;

	static {
		s = new XStream();
		s.alias("StimSpec", GaborSpec.class);
		s.useAttributeFor("animation", boolean.class);
	}

	public String toXml () {
		return GaborSpec.toXml(this);
	}

	public static String toXml (GaborSpec spec) {
		return s.toXML(spec);
	}

	public static GaborSpec fromXml (String xml) {
		GaborSpec g = (GaborSpec)s.fromXML(xml);
		return g;
	}

	@Override
	public XMLizable getFromXml(String xml) {
		return fromXml(xml);
	}

	public GaborSpec() {}

	public GaborSpec(GaborSpec d) {
		xCenter = d.getXCenter();
		yCenter = d.getYCenter();
		orientation = d.getOrientation();
		frequency = d.getFrequency();
		phase = d.getPhase();
		size = d.getDiameter();
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
	public double getDiameter() {
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