package org.xper.allen.nafc.vo;

public class NoisyMStickNAFCTrialGenData {
	int numDistractors;
	int numQMDistractors;
	int numRandDistractors;
	int numQMCategories;
	int numMMCategories;
	double sampleScaleUpperLim;
	double distractorScaleUpperLim;
	double[] sampleRadiusLim;
	double eyeWinSize;
	double[] choiceRadiusLim;
	double[] distractorDistanceLim;
	
	public NoisyMStickNAFCTrialGenData(int numDistractors, int numQMDistractors, int numRandDistractors,
			int numQMCategories, int numMMCategories, double sampleScaleUpperLim, double distractorScaleUpperLim,
			double[] sampleRadiusLim, double eyeWinSize, double[] choiceRadiusLim, double[] distractorDistanceLim) {
		super();
		this.numDistractors = numDistractors;
		this.numQMDistractors = numQMDistractors;
		this.numRandDistractors = numRandDistractors;
		this.numQMCategories = numQMCategories;
		this.numMMCategories = numMMCategories;
		this.sampleScaleUpperLim = sampleScaleUpperLim;
		this.distractorScaleUpperLim = distractorScaleUpperLim;
		this.sampleRadiusLim = sampleRadiusLim;
		this.eyeWinSize = eyeWinSize;
		this.choiceRadiusLim = choiceRadiusLim;
		this.distractorDistanceLim = distractorDistanceLim;
	}
	//TODO: noise specification
	public int getNumDistractors() {
		return numDistractors;
	}
	public void setNumDistractors(int numDistractors) {
		this.numDistractors = numDistractors;
	}
	public int getNumQMDistractors() {
		return numQMDistractors;
	}
	public void setNumQMDistractors(int numQMDistractors) {
		this.numQMDistractors = numQMDistractors;
	}
	public int getNumRandDistractors() {
		return numRandDistractors;
	}
	public void setNumRandDistractors(int numRandDistractors) {
		this.numRandDistractors = numRandDistractors;
	}
	public int getNumQMCategories() {
		return numQMCategories;
	}
	public void setNumQMCategories(int numQMCategories) {
		this.numQMCategories = numQMCategories;
	}
	public int getNumMMCategories() {
		return numMMCategories;
	}
	public void setNumMMCategories(int numMMCategories) {
		this.numMMCategories = numMMCategories;
	}
	public double getSampleScaleUpperLim() {
		return sampleScaleUpperLim;
	}
	public void setSampleScaleUpperLim(double sampleScaleUpperLim) {
		this.sampleScaleUpperLim = sampleScaleUpperLim;
	}
	public double getDistractorScaleUpperLim() {
		return distractorScaleUpperLim;
	}
	public void setDistractorScaleUpperLim(double distractorScaleUpperLim) {
		this.distractorScaleUpperLim = distractorScaleUpperLim;
	}
	public double[] getSampleRadiusLim() {
		return sampleRadiusLim;
	}
	public void setSampleRadiusLim(double[] sampleRadiusLim) {
		this.sampleRadiusLim = sampleRadiusLim;
	}
	public double getEyeWinSize() {
		return eyeWinSize;
	}
	public void setEyeWinSize(double eyeWinSize) {
		this.eyeWinSize = eyeWinSize;
	}
	public double[] getChoiceRadiusLim() {
		return choiceRadiusLim;
	}
	public void setChoiceRadiusLim(double[] choiceRadiusLim) {
		this.choiceRadiusLim = choiceRadiusLim;
	}
	public double[] getDistractorDistanceLim() {
		return distractorDistanceLim;
	}
	public void setDistractorDistanceLim(double[] distractorDistanceLim) {
		this.distractorDistanceLim = distractorDistanceLim;
	}
}
