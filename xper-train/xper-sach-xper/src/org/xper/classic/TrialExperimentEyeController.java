package org.xper.classic;

import java.util.concurrent.atomic.AtomicInteger;

import org.xper.Dependency;
import org.xper.experiment.EyeController;
import org.xper.eye.listener.EyeEventListener;
import org.xper.eye.vo.EyePosition;
import org.xper.time.TimeUtil;


/**
 * Eye logic for trial experiments including waiting for initial eye in, waiting
 * for the eye in and hold time and checking for eye in during experiment.
 * 
 * It's used by SlideTrialExperiment to control eye behavior.
 * 
 * @author Zhihong Wang
 * 
 */
public class TrialExperimentEyeController implements EyeController,
		EyeEventListener {

	/**
	 * Interval in ms between successive eye signal check.
	 */
	@Dependency
	int checkInterval = 10;
	@Dependency
	TimeUtil localTimeUtil;

	AtomicInteger progress = new AtomicInteger(-1);
	static final int INITIAL_EYE_IN = 1;
	static final int EYE_IN_AND_HOLD = 2;
	AtomicInteger mostRecentEyeEvent = new AtomicInteger(-1);
	static final int EYE_IN = 1;
	static final int EYE_OUT = 2;

	/**
	 * This runs in experiment thread.
	 * 
	 * @param target
	 *            in microseconds.
	 * @return true if eye in before timeout.
	 */
	public boolean waitInitialEyeIn(long target) {
		mostRecentEyeEvent.set(-1);
		
		progress.set(INITIAL_EYE_IN);
		
		long current = localTimeUtil.currentTimeMicros();

		while (mostRecentEyeEvent.get() != EYE_IN) {
			if (current >= target)
				return false;
			try {
				Thread.sleep(target - current > checkInterval ? checkInterval
						: target - current);
			} catch (InterruptedException e) {
			}
			current = localTimeUtil.currentTimeMicros();
		}
		return true;
	}

	/**
	 * This runs in experiment thread.
	 * 
	 * @return true if eye out did not happen before timeout.
	 */
	public boolean waitEyeInAndHold(long target) {
		progress.set(EYE_IN_AND_HOLD);

		long current = localTimeUtil.currentTimeMicros();

		while (mostRecentEyeEvent.get() == EYE_IN) {
			if (current >= target)
				return true;
			try {
				Thread.sleep(target - current > checkInterval ? checkInterval
						: target - current);
			} catch (InterruptedException e) {
			}
			current = localTimeUtil.currentTimeMicros();
		}
		return false;
	}

	/**
	 * This runs in experiment thread.
	 */
	public boolean isEyeIn() {
		return (mostRecentEyeEvent.get() == EYE_IN);
	}

	/**
	 * This runs in EyeSampler thread.
	 */
	public void eyeIn(EyePosition eyePos, long timestamp) {
		if (progress.get() <= INITIAL_EYE_IN) {
			mostRecentEyeEvent.set(EYE_IN);
		}
	}

	/**
	 * This runs in EyeSampler thread.
	 */
	public void eyeOut(EyePosition eyePos, long timestamp) {
		mostRecentEyeEvent.set(EYE_OUT);
	}

	public int getCheckInterval() {
		return checkInterval;
	}

	public void setCheckInterval(int checkInterval) {
		this.checkInterval = checkInterval;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}
}
