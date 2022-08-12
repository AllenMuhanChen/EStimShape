package org.xper.rfplot;

import com.thoughtworks.xstream.XStream;

public class RFPlotStimSpec {
	/**
	 * Class name of the RFPlotObject
	 */
	String stimClass;
	/**
	 * Spec for the RFPlotObject
	 */
	String stimSpec;
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("RFPlotSpec", RFPlotStimSpec.class);
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
