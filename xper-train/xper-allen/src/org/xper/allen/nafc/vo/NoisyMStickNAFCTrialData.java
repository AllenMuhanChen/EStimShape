package org.xper.allen.nafc.vo;

import com.thoughtworks.xstream.XStream;

public class NoisyMStickNAFCTrialData {
	
	public NoisyMStickNAFCTrialData(NoisyMStickNAFCTrialGenData trialGenData, NoiseData noiseData) {
		this.trialGenData = trialGenData;
		this.noiseData = noiseData;
	}
	
	public NoisyMStickNAFCTrialData() {
	}

	NoisyMStickNAFCTrialGenData trialGenData;
	NoiseData noiseData;
	
	static XStream s = new XStream();
	
	static {
		s.alias("NoisyMStickNAFCTrialData", NoisyMStickNAFCTrialData.class);
	}
	
	public static String toXml(NoisyMStickNAFCTrialData data) {
		return s.toXML(data);
	}
	
	public String toXml() {
		return toXml(this);
	}
	
	public NoisyMStickNAFCTrialGenData getTrialGenData() {
		return trialGenData;
	}
	public void setTrialGenData(NoisyMStickNAFCTrialGenData trialGenData) {
		this.trialGenData = trialGenData;
	}
	public NoiseData getNoiseData() {
		return noiseData;
	}
	public void setNoiseData(NoiseData noiseData) {
		this.noiseData = noiseData;
	}
}
