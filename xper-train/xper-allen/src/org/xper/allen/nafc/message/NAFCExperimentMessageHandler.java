package org.xper.allen.nafc.message;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.allen.nafc.console.NAFCTrialStatistics;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;

public class NAFCExperimentMessageHandler extends TrialExperimentMessageHandler{
	AtomicBoolean sampleOn = new AtomicBoolean(false);
	AtomicBoolean choicesOn = new AtomicBoolean(false);
	AtomicReference<double[]> targetEyeWindowSize = new AtomicReference<double[]>();
	AtomicReference<Coordinates2D[]> targetPosition = new AtomicReference<Coordinates2D[]>();

	AtomicReference<NAFCTrialStatistics> trialStat = new AtomicReference<NAFCTrialStatistics>();
	
	public NAFCExperimentMessageHandler() {
		trialStat.set(new NAFCTrialStatistics());
	}

	@Override
	public boolean handleMessage(BehMsgEntry msg) {
		if ("EyeDeviceMessage".equals(msg.getType())) {
			handleEyeDeviceMessage(msg);
			return true;
		} else if ("FixationPointOn".equals(msg.getType())){
			fixationOn.set(true);
			return true;
		} else if ("EyeInBreak".equals(msg.getType()) ||
				"EyeInHoldFail".equals(msg.getType()) ||
				"InitialEyeInFail".equals(msg.getType()) ||
				"TrialComplete".equals(msg.getType())) {
			fixationOn.set(false);
			return true;
		} else if ("EyeWindowMessage".equals(msg.getType())) {
			handleEyeWindowMessage(msg);
			return true;
		} else if ("EyeZeroMessage".equals(msg.getType())) {
			handleEyeZeroMessage(msg);
			return true;
		} else if ("TrialStatistics".equals(msg.getType())) {
			handleTrialStatistics(msg);
			return true;
		} else if ("TrialInit".equals(msg.getType())) {
			inTrial.set(true);
			return true;
		} else if ("TrialStop".equals(msg.getType())) {
			inTrial.set(false);
			return true;
		} else if ("EyeInEvent".equals(msg.getType())) {
			eyeIn.set(true);
			return true;
		} else if ("EyeOutEvent".equals(msg.getType())) {
			eyeIn.set(false);
			return true;
		} else if ("SampleOn".equals(msg.getType())) { 
			sampleOn.set(true);
			fixationOn.set(false);
			return true;
		} else if ("SampleOff".equals(msg.getType())) { 
			sampleOn.set(false);
			return true;
		} else if ("ChoicesOn".equals(msg.getType())){
			choicesOn.set(true);
			NAFCChoiceMessage m = NAFCChoiceMessage.fromXml(msg.getMsg());
			targetPosition.set(m.getTargetEyeWinCoords());
			targetEyeWindowSize.set(m.getTargetEyeWinSize());
			return true;
		} else if ("ChoicesOff".equals(msg.getType())) {
			choicesOn.set(false);
			return true;
		} else {
			return false;
		}
	}
	
	protected void handleTrialStatistics(BehMsgEntry ent) {
		trialStat.set(NAFCTrialStatistics.fromXml(ent.getMsg()));
	}

	public boolean isSampleOn() {
		return sampleOn.get();
	}

	public boolean isChoicesOn() {
		return choicesOn.get();
	}


	public double[] getTargetEyeWindowSize() {
		return targetEyeWindowSize.get();
	}


	public Coordinates2D[] getTargetPosition() {
		return targetPosition.get();
	}

	public NAFCTrialStatistics getNAFCTrialStatistics() {
		return this.trialStat.get();
	}

	
}
