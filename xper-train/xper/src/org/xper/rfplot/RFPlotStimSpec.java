package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class RFPlotStimSpec {
	/**
	 * Class name of the RFPlotObject
	 */
	String stimClass;
	/**
	 * Spec for the RFPlotObject
	 */
	String stimSpec;

	public RFPlotStimSpec() {
	}

	public RFPlotStimSpec(String stimClass, String stimSpec) {
		this.stimClass = stimClass;
		this.stimSpec = stimSpec;
	}

	boolean animation = true;
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", RFPlotStimSpec.class);
		s.useAttributeFor("animation", boolean.class);
	}
	
	public String toXml () {
		return RFPlotStimSpec.toXml(this);
	}
	
	public static String toXml (RFPlotStimSpec spec) {
		return s.toXML(spec);
	}
	
	public static RFPlotStimSpec fromXml (String xml) {
		if (xml == null) return null;
		RFPlotStimSpec spec = (RFPlotStimSpec)s.fromXML(xml);
		return spec;
	}

	public static RFPlotStimSpec fromRFPlotDrawable(RFPlotDrawable drawable){
		String stimSpec = drawable.getSpec();
		String stimClass = drawable.getClass().getName();

		return new RFPlotStimSpec(stimClass, stimSpec);
	}

	public static String getStimSpecFromRFPlotDrawable(RFPlotDrawable drawable){
		return RFPlotStimSpec.fromRFPlotDrawable(drawable).toXml();
	}
	
	public String getStimClass() {
		return stimClass;
	}
	public void setStimClass(String stimClass) {
		this.stimClass = stimClass;
	}
	public String getStimSpec() {
		return stimSpec;
	}
	public void setStimSpec(String stimSpec) {
		this.stimSpec = stimSpec;
	}
}
