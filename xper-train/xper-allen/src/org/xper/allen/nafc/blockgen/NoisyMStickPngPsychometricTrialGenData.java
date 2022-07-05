package org.xper.allen.nafc.blockgen;

public class NoisyMStickPngPsychometricTrialGenData{
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