package org.xper.allen.experiment.saccade;

import java.sql.Timestamp;

import org.xper.Dependency;
import org.xper.allen.console.TargetEventListener;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.juice.Juice;


public class SaccadeJuiceController implements TrialEventListener, TargetEventListener {
	
	@Dependency
	Juice juice;

	public void eyeInBreak(long timestamp, TrialContext context) {
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
	}

	public void trialComplete(long timestamp, TrialContext context) {

	}
	
	public void trialInit(long timestamp, TrialContext context) {
	}

	public void trialStart(long timestamp, TrialContext context) {
	}

	public void trialStop(long timestamp, TrialContext context) {
	}

	public Juice getJuice() {
		return juice;
	}

	public void setJuice(Juice juice) {
		this.juice = juice;
	}

	@Override
	public void targetOn(long timestamp, TrialContext context) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void targetOff(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void targetSelectionEyeFail(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void targetSelectionEyeBreak(long timestamp) {
		// TODO Auto-generated method stub
		
	}

	@Override
	public void targetSelectionDone(long timestamp) {
		juice.deliver();
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString());
		
	}
}
