package org.xper.allen.experiment.twoac;

import org.xper.allen.console.SaccadeTargetMessage;
import org.xper.drawing.Coordinates2D;

import com.thoughtworks.xstream.XStream;

public class TwoACChoiceMessage {
	long[] stimObjDataId;
	Coordinates2D[] targetEyeWinCoords;
	double[] targetEyeWinSize;
	RewardPolicy rewardPolicy;
	
	public TwoACChoiceMessage(long[] stimObjDataId, Coordinates2D[] targetEyeWinCoords, double[] targetEyeWinSize,
			RewardPolicy rewardPolicy) {
		super();
		this.stimObjDataId = stimObjDataId;
		this.targetEyeWinCoords = targetEyeWinCoords;
		this.targetEyeWinSize = targetEyeWinSize;
		this.rewardPolicy = rewardPolicy;
	}

	public long[] getStimObjDataId() {
		return stimObjDataId;
	}

	public void setStimObjDataId(long[] stimObjDataId) {
		this.stimObjDataId = stimObjDataId;
	}

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

	public RewardPolicy getRewardPolicy() {
		return rewardPolicy;
	}

	public void setRewardPolicy(RewardPolicy rewardPolicy) {
		this.rewardPolicy = rewardPolicy;
	}
	
	transient static XStream s = new XStream();
	
	static {
		s.alias("TwoACChoiceMessage", TwoACChoiceMessage.class);
		s.alias("Coordinates2D", Coordinates2D.class);
	}
	
	public static String toXml(TwoACChoiceMessage msg) {
		return s.toXML(msg);
	}
	
	public String toXml() {
		return s.toXML(this);
	}
}
