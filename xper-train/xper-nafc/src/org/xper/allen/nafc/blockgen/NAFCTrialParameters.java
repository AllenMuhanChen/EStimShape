package org.xper.allen.nafc.blockgen;

public class NAFCTrialParameters {
	private Lims sampleDistanceLims;
	private Lims choiceDistanceLims;
	private double size;
	private double eyeWinSize;

	public NAFCTrialParameters(NAFCTrialParameters other) {
		this.sampleDistanceLims = other.sampleDistanceLims;
		this.choiceDistanceLims = other.choiceDistanceLims;
		this.size = other.size;
		this.eyeWinSize = other.eyeWinSize;
	}

	public NAFCTrialParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinSize) {
		super();
		this.sampleDistanceLims = sampleDistanceLims;
		this.choiceDistanceLims = choiceDistanceLims;
		this.size = size;
		this.eyeWinSize = eyeWinSize;
	}

	public NAFCTrialParameters() {
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

	public double getEyeWinSize() {
		return eyeWinSize;
	}

	public void setEyeWinSize(double eyeWinSize) {
		this.eyeWinSize = eyeWinSize;
	}
}