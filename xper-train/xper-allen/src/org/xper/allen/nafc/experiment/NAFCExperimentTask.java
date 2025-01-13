package org.xper.allen.nafc.experiment;

import org.xper.drawing.Coordinates2D;
import org.xper.experiment.ExperimentTask;

/**
 * Holds information that goes to both the drawing controller (in the form of a string XML. It is the job of the Graphics Object to decode this, like RFPlotGaussianObject)
 * and the rest of the code.
 * @author allenchen
 *
 */
public class NAFCExperimentTask extends ExperimentTask {

	Coordinates2D[] targetEyeWinCoords;
	double[] targetEyeWinSize;
	//double[] duration;
	String eStimSpec;
	String sampleSpec;
	String[] choiceSpec;
	long sampleSpecId;
	long[] choiceSpecId;
	RewardPolicy rewardPolicy;
	int[] rewardList;


	public String getSampleSpec() {
		return sampleSpec;
	}

	public void setSampleSpec(String sampleSpec) {
		this.sampleSpec = sampleSpec;
	}

	public String[] getChoiceSpec() {
		return choiceSpec;
	}

	public void setChoiceSpec(String[] choiceSpec) {
		this.choiceSpec = choiceSpec;
	}

	/*
	public Coordinates2D parseCoords() {
		GaussSpec g = GaussSpec.fromXml(this.getStimSpec());
		Coordinates2D coords = new Coordinates2D(g.getXCenter(),g.getYCenter());
		return coords;
	}
	*/
	public Coordinates2D[] getTargetEyeWinCoords() {
		return targetEyeWinCoords;
	}

	public void setTargetEyeWinCoords(Coordinates2D[] targetEyeWinCoords) {
		this.targetEyeWinCoords = targetEyeWinCoords;
	}

	public double[] getTargetEyeWinSize() {
		return targetEyeWinSize;
	}

	public void setTargetEyeWinSize(double[] targetEyeWinSize) {
		this.targetEyeWinSize = targetEyeWinSize;
	}
/*
	public void setDuration(double[] duration) {
		this.duration = duration;
	}

	public double[] getDuration() {
		return duration;
	}
*/
	public String geteStimSpec() {
		return eStimSpec;
	}

	public void seteStimSpec(String eStimSpec) {
		this.eStimSpec = eStimSpec;
	}

	public RewardPolicy getRewardPolicy() {
		return rewardPolicy;
	}

	public void setRewardPolicy(RewardPolicy rewardPolicy) {
		this.rewardPolicy = rewardPolicy;
	}

	public long getSampleSpecId() {
		return sampleSpecId;
	}

	public void setSampleSpecId(long sampleSpecId) {
		this.sampleSpecId = sampleSpecId;
	}

	public long[] getChoiceSpecId() {
		return choiceSpecId;
	}

	public void setChoiceSpecId(long[] choiceSpecId) {
		this.choiceSpecId = choiceSpecId;
	}

	public int[] getRewardList() {
		return rewardList;
	}

	public void setRewardList(int[] rewardList) {
		this.rewardList = rewardList;
	}



}