package org.xper.allen.nafc.blockgen;

import com.thoughtworks.xstream.XStream;

public class NAFCTrialParameters {
	private Lims sampleDistanceLims;
	private Lims choiceDistanceLims;
	private double size;
	private double eyeWinRadius;

	public NAFCTrialParameters(NAFCTrialParameters other) {
		this.sampleDistanceLims = other.sampleDistanceLims;
		this.choiceDistanceLims = other.choiceDistanceLims;
		this.size = other.size;
		this.eyeWinRadius = other.eyeWinRadius;
	}

	public NAFCTrialParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinRadius) {
		super();
		this.sampleDistanceLims = sampleDistanceLims;
		this.choiceDistanceLims = choiceDistanceLims;
		this.size = size;
		this.eyeWinRadius = eyeWinRadius;
	}

	public NAFCTrialParameters() {
	}

	static XStream s = new XStream();

	static {
		s.alias("NAFCTrialParameters", NAFCTrialParameters.class);
	}

	public String toXml(NAFCTrialParameters data) {
		return s.toXML(data);
	}

	public String toXml() {
		return toXml(this);
	}

	public NAFCTrialParameters fromXml(String xml) {
		return (NAFCTrialParameters)s.fromXML(xml);
	}

	public Lims getSampleDistanceLims() {
		return sampleDistanceLims;
	}

	public void setSampleDistanceLims(Lims sampleDistanceLims) {
		this.sampleDistanceLims = sampleDistanceLims;
	}

	public Lims getChoiceDistanceLims() {
		return choiceDistanceLims;
	}

	public void setChoiceDistanceLims(Lims choiceDistanceLims) {
		this.choiceDistanceLims = choiceDistanceLims;
	}

	public double getSize() {
		return size;
	}

	public void setSize(double size) {
		this.size = size;
	}

	public double getEyeWinRadius() {
		return eyeWinRadius;
	}

	public void setEyeWinRadius(double eyeWinRadius) {
		this.eyeWinRadius = eyeWinRadius;
	}
}