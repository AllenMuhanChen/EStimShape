package org.xper.classic;

import org.xper.classic.vo.TrialContext;

public interface TrialEventListener {
	
	/**
	 * 
	 * @param timestamp in microseconds
	 */
	public void trialInit (long timestamp, TrialContext context);
	
	/**
	 * 
	 * @param timestamp in microseconds
	 */
	public void trialStart (long timestamp, TrialContext context);
	/**
	 * 
	 * @param timestamp in microseconds
	 */
	public void fixationPointOn (long timestamp, TrialContext context);
	/**
	 * 
	 * @param timestamp in microseconds
	 */
	public void initialEyeInFail (long timestamp, TrialContext context);
	public void initialEyeInSucceed (long timestamp, TrialContext context);
	
	public void eyeInHoldFail (long timestamp, TrialContext context);
	public void fixationSucceed (long timestamp, TrialContext context);
	public void eyeInBreak (long timestamp, TrialContext context);
	/**
	 * Trial was completed without eye fail or eye break.
	 * @param timestamp in microseconds
	 */
	public void trialComplete (long timestamp, TrialContext context);
	public void trialStop (long timestamp, TrialContext context);
}
