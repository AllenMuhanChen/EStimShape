package org.xper.allen.console;

import java.util.concurrent.atomic.AtomicBoolean;

import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.db.vo.BehMsgEntry;

public class SaccadeExperimentMessageHandler extends TrialExperimentMessageHandler{
	protected AtomicBoolean targetOn = new AtomicBoolean(false);
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
		} else if ("TargetOn".equals(msg.getType())) {  //AC added SlideOn 
			targetOn.set(true);
			return true;
		} else if ("TargetOff".equals(msg.getType())) {
			targetOn.set(false);
			return true;
		} else {
			return false;
		}
	}
	
	public boolean isTargetOn() {
		return targetOn.get();
	}
}
