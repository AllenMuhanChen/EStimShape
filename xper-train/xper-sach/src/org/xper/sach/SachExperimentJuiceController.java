package org.xper.sach;

import java.sql.Timestamp;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.TrialContext;
import org.xper.juice.DynamicJuice;
import org.xper.sach.vo.SachTrialContext;

public class SachExperimentJuiceController implements TrialEventListener {
	static Logger logger = Logger.getLogger(SachExperimentJuiceController.class);
	
	@Dependency
	DynamicJuice juice;

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
		SachTrialContext c = (SachTrialContext)context;
		long reward = c.getReward();
		juice.setReward(reward);
		juice.deliver();
		System.out.println("Juice delivered " + reward + " @ " + new Timestamp(timestamp/1000).toString());
	}
	
	public void trialInit(long timestamp, TrialContext context) {
	}

	public void trialStart(long timestamp, TrialContext context) {
	}

	public void trialStop(long timestamp, TrialContext context) {
	}

	public DynamicJuice getJuice() {
		return juice;
	}

	public void setJuice(DynamicJuice juice) {
		this.juice = juice;
	}

}
