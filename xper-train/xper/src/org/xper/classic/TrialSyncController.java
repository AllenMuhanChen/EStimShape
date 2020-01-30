package org.xper.classic;

import java.sql.Timestamp;

import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.trialsync.TrialSync;


public class TrialSyncController implements TrialEventListener {
	
	@Dependency
	TrialSync trialSync;

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
		trialSync.startTrialSyncPulse();
		System.out.println("Trial syncing started (trialInit) @ " + new Timestamp(timestamp/1000).toString());
	}

	public void trialStart(long timestamp, TrialContext context) {
	}

	public void trialStop(long timestamp, TrialContext context) {
		trialSync.stopTrialSyncPulse();;
		System.out.println("Trial syncing stopped (trialStop) @ " + new Timestamp(timestamp/1000).toString());
	}

	public TrialSync getTrialSync() {
		return trialSync;
	}

	public void setTrialSync(TrialSync trialSync) {
		this.trialSync = trialSync;
	}
}
