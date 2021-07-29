package org.xper.allen.twoac.console;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.allen.saccade.db.vo.SaccadeTrialStatistics;
import org.xper.allen.twoac.TwoACChoiceMessage;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;

public class TwoACExperimentMessageHandler extends TrialExperimentMessageHandler{
	AtomicBoolean sampleOn = new AtomicBoolean(false);
	AtomicBoolean choicesOn = new AtomicBoolean(false);
	AtomicReference<double[]> targetEyeWindowSize = new AtomicReference<double[]>();
	AtomicReference<Coordinates2D[]> targetPosition = new AtomicReference<Coordinates2D[]>();

	AtomicReference<SaccadeTrialStatistics> trialStat = new AtomicReference<SaccadeTrialStatistics>();
	
	public TwoACExperimentMessageHandler() {
		trialStat.set(new SaccadeTrialStatistics());
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
			TwoACChoiceMessage m = TwoACChoiceMessage.fromXml(msg.getMsg());
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

	public SaccadeTrialStatistics getTrialStatistics() {
		return trialStat.get();
	}

}
