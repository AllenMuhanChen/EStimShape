package org.xper.classic;

import java.sql.Timestamp;

import org.apache.log4j.Logger;
import org.xper.classic.vo.TrialContext;

public class TrialEventLogger implements TrialEventListener {
	static Logger logger = Logger.getLogger(TrialEventLogger.class);

	public void eyeInHoldFail(long timestamp, TrialContext context) {
		log("eyeInHoldFail", timestamp);
	}

	public void fixationPointOn(long timestamp, TrialContext context) {
		log("fixationPointOn", timestamp);
	}

	public void fixationSucceed(long timestamp, TrialContext context) {
		log("fixationSucceed", timestamp);
	}

	public void initialEyeInFail(long timestamp, TrialContext context) {
		log("initialEyeInFail", timestamp);
	}

	public void initialEyeInSucceed(long timestamp, TrialContext context) {
		log("initialEyeInSucceed", timestamp);
	}

	public void trialComplete(long timestamp, TrialContext context) {
		log("trialComplete", timestamp);
	}
	
	public void trialInit(long timestamp, TrialContext context) {
		log("trialInit", timestamp);
	}

	public void trialStart(long timestamp, TrialContext context) {
		log("trialStart", timestamp);
	}

	public void trialStop(long timestamp, TrialContext context) {
		log("trialStop", timestamp);
	}

	protected void log(String event, long timestamp) {
		logger.info(event + ": " + new Timestamp(timestamp/1000).toString());
	}

	public void eyeInBreak(long timestamp, TrialContext context) {
		log("eyeInBreak", timestamp);
	}
}
