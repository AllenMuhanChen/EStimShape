package org.xper.allen.saccade.console;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.allen.saccade.db.vo.SaccadeTrialStatistics;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.classic.vo.TrialStatistics;
import org.xper.db.vo.BehMsgEntry;
import org.xper.drawing.Coordinates2D;

/**
 * Provides methods for reading behmsg entries and allowing any part of xper to access them (the console) 
 */
public class SaccadeExperimentMessageHandler extends TrialExperimentMessageHandler{
	AtomicBoolean targetOn = new AtomicBoolean(false);
	AtomicReference<Coordinates2D> targetPosition = new AtomicReference<Coordinates2D>(new Coordinates2D(0,0));
	AtomicReference<Double> targetEyeWindowSize = new AtomicReference<Double>((double) 0);
	AtomicReference<SaccadeTrialStatistics> trialStat = new AtomicReference<SaccadeTrialStatistics>();
	
	public SaccadeExperimentMessageHandler() {
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
		} else if ("TargetOn".equals(msg.getType())) { //AC added targetOn
			targetOn.set(true);
			SaccadeTargetMessage m = SaccadeTargetMessage.fromXml(msg.getMsg());
			targetPosition.set(m.getTargetPos());
			targetEyeWindowSize.set(m.getTargetEyeWindowSize());
			return true;
		} else if ("TargetOff".equals(msg.getType())) {
			targetOn.set(false);
			return true;
		} else {
			return false;
		}
	}
	
	public SaccadeTrialStatistics getTrialStatistics() {
		return trialStat.get();
	}
	
	protected void handleTrialStatistics(BehMsgEntry ent) {
		trialStat.set(SaccadeTrialStatistics.fromXml(ent.getMsg()));
	}
	
	public boolean isTargetOn() {
		return targetOn.get();
	}
	
	public Coordinates2D getTargetPosition() {
		return targetPosition.get();	
	}
	
	public double getTargetEyeWindowSize() {
		return targetEyeWindowSize.get();
	}
}
