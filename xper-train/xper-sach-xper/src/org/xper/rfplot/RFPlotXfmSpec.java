package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import com.thoughtworks.xstream.XStream;

public class RFPlotXfmSpec {
	
	Coordinates2D translation;
	Coordinates2D scale;
	float rotation;
	RGBColor color;
	
	transient static XStream s;
	
	static RFPlotXfmSpec defaultXmlSpec;
	
	static {
		s = new XStream();
		s.alias("RFPlotXfmSpec", RFPlotXfmSpec.class);
		
		defaultXmlSpec = new RFPlotXfmSpec();
		defaultXmlSpec.setColor(new RGBColor(0f, 0f, 0f));
		defaultXmlSpec.setScale(new Coordinates2D(1.0, 1.0));
		defaultXmlSpec.setRotation(0f);
		defaultXmlSpec.setTranslation(new Coordinates2D(0, 0));
	}
	
	public String toXml () {
		return RFPlotXfmSpec.toXml(this);
	}
	
	public static String toXml (RFPlotXfmSpec spec) {
		return s.toXML(spec);
	}
	
	public static RFPlotXfmSpec fromXml (String xml) {
		if (xml == null) return defaultXmlSpec;
		
		RFPlotXfmSpec spec = (RFPlotXfmSpec)s.fromXML(xml);
		return spec;
	}
	
	public Coordinates2D getTranslation() {
		return translation;
	}

	public void setTranslation(Coordinates2D translation) {
		this.translation = translation;
	}

	public Coordinates2D getScale() {
		return scale;
	}

	public void setScale(Coordinates2D scale) {
		this.scale = scale;
	}

	public float getRotation() {
		return rotation;
	}

	public void setRotation(float rotation) {
		this.rotation = rotation;
	}

	public RGBColor getColor() {
		return color;
	}

	public void setColor(RGBColor color) {
		this.color = color;
	}
}
