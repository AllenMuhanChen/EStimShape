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

class NoisyMStickPngPsychometricTrialGenData{
	public NoisyMStickPngPsychometricTrialGenData(double sampleDistanceLowerLim, double sampleDistanceUpperLim,
			double choiceDistanceLowerLim, double choiceDistanceUpperLim, double sampleScale, double eyeWinSize) {
		super();
		this.sampleDistanceLowerLim = sampleDistanceLowerLim;
		this.sampleDistanceUpperLim = sampleDistanceUpperLim;
		this.choiceDistanceLowerLim = choiceDistanceLowerLim;
		this.choiceDistanceUpperLim = choiceDistanceUpperLim;
		this.sampleScale = sampleScale;
		this.eyeWinSize = eyeWinSize;
	}
	double sampleDistanceLowerLim;
	double sampleDistanceUpperLim;
	double choiceDistanceLowerLim;
	double choiceDistanceUpperLim;
	double sampleScale;
	double eyeWinSize;
	
	public double getSampleDistanceLowerLim() {
		return sampleDistanceLowerLim;
	}
	public void setSampleDistanceLowerLim(double sampleDistanceLowerLim) {
		this.sampleDistanceLowerLim = sampleDistanceLowerLim;
	}
	public double getSampleDistanceUpperLim() {
		return sampleDistanceUpperLim;
	}
	public void setSampleDistanceUpperLim(double sampleDistanceUpperLim) {
		this.sampleDistanceUpperLim = sampleDistanceUpperLim;
	}
	public double getChoiceDistanceLowerLim() {
		return choiceDistanceLowerLim;
	}
	public void setChoiceDistanceLowerLim(double choiceDistanceLowerLim) {
		this.choiceDistanceLowerLim = choiceDistanceLowerLim;
	}
	public double getChoiceDistanceUpperLim() {
		return choiceDistanceUpperLim;
	}
	public void setChoiceDistanceUpperLim(double choiceDistanceUpperLim) {
		this.choiceDistanceUpperLim = choiceDistanceUpperLim;
	}
	public double getSampleScale() {
		return sampleScale;
	}
	public void setSampleScale(double sampleScale) {
		this.sampleScale = sampleScale;
	}
	public double getEyeWinSize() {
		return eyeWinSize;
	}
	public void setEyeWinSize(double eyeWinSize) {
		this.eyeWinSize = eyeWinSize;
	}
}