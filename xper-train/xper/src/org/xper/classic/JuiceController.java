package org.xper.classic;

import java.sql.Timestamp;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.juice.Juice;


public class JuiceController implements TrialEventListener {
	
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
		juice.deliver();
		System.out.println("Juice delivered @ " + new Timestamp(timestamp/1000).toString());
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
}
