package org.xper.allen.nafc.blockgen;

public class NoisyMStickPngPsychometricTrialGenData{

	DistanceLims sampleDistanceLims;
	DistanceLims choiceDistanceLims;
	double sampleScale;
	double eyeWinSize;
	

	public NoisyMStickPngPsychometricTrialGenData(DistanceLims sampleDistanceLims, DistanceLims choiceDistanceLims,
			double sampleScale, double eyeWinSize) {
		super();
		this.sampleDistanceLims = sampleDistanceLims;
		this.choiceDistanceLims = choiceDistanceLims;
		this.sampleScale = sampleScale;
		this.eyeWinSize = eyeWinSize;
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
	public DistanceLims getSampleDistanceLims() {
		return sampleDistanceLims;
	}
	public void setSampleDistanceLims(DistanceLims sampleDistanceLims) {
		this.sampleDistanceLims = sampleDistanceLims;
	}
	public DistanceLims getChoiceDistanceLims() {
		return choiceDistanceLims;
	}
	public void setChoiceDistanceLims(DistanceLims choiceDistanceLims) {
		this.choiceDistanceLims = choiceDistanceLims;
	}
}