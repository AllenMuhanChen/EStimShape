package org.xper.classic;

import java.lang.management.ManagementFactory;
import java.lang.management.MemoryMXBean;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.classic.vo.TrialContext;
import org.xper.time.TimeUtil;

public class JvmManager implements TrialEventListener {
	static Logger logger = Logger.getLogger(JvmManager.class);
	
	@Dependency
	TimeUtil localTimeUtil;
	
	MemoryMXBean memory = ManagementFactory.getMemoryMXBean();

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
		long memBefore = memory.getHeapMemoryUsage().getUsed();
		long before = localTimeUtil.currentTimeMicros();
		memory.gc();
		long after = localTimeUtil.currentTimeMicros();
		long memAfter = memory.getHeapMemoryUsage().getUsed();
		
		logger.info("Time spent in gc: " + (after - before)/1000 + " ms.");
		logger.info("Memory before gc: " + memBefore);
		logger.info("Memory after gc: " + memAfter);
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}
}
