package org.xper.allen.nafc.blockgen;

import org.xper.allen.nafc.vo.NoiseData;

import com.thoughtworks.xstream.XStream;

public class NoisyMStickPngPsychometricTrialData {
	
	NoiseData noiseData;
	NoisyMStickPngPsychometricTrialGenData trialGenData;
	static XStream s = new XStream();
	
	static {
		s.alias("NoisyMStickPngPsychometricTrialData", NoisyMStickPngPsychometricTrialData.class);
	}
	
	public NoisyMStickPngPsychometricTrialData(NoiseData noiseData,
			NoisyMStickPngPsychometricTrialGenData trialGenData) {
		super();
		this.noiseData = noiseData;
		this.trialGenData = trialGenData;
	}

	public String toXml(NoisyMStickPngPsychometricTrialData data) {
		return s.toXML(data);
	}

	public String toXml() {
		return toXml(this);
	}

	
	public NoiseData getNoiseData() {
		return noiseData;
	}

	public void setNoiseData(NoiseData noiseData) {
		this.noiseData = noiseData;
	}

	public NoisyMStickPngPsychometricTrialGenData getTrialGenData() {
		return trialGenData;
	}

	public void setTrialGenData(NoisyMStickPngPsychometricTrialGenData trialGenData) {
		this.trialGenData = trialGenData;
	}
	
	

}