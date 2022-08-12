package org.xper.eye;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.time.TimeUtil;


public class RobustEyeTargetSelector implements EyeSamplerEventListener, EyeTargetSelector {

	/**
	 * Interval in ms between successive eye signal check.
	 */
	@Dependency
	int checkInterval = 10;
	@Dependency
	EyeInStrategy eyeInstrategy;
	@Dependency
	TimeUtil localTimeUtil;
	
	/**
	 * In milliseconds.
	 */
	@Dependency
	double targetOutTimeThreshold;

	/**
	 * In milliseconds.
	 */
	@Dependency
	double targetInTimeThreshold;
	
	boolean eyeOutStatus[];
	boolean eyeInStatus[];
	boolean eyeOutEvent[];
	boolean eyeInEvent[];
	long eyeOutLocalTime[];
	long eyeInLocalTime[];
	
	AtomicBoolean startPicking = new AtomicBoolean(false);
	AtomicBoolean checkHolding = new AtomicBoolean(false);
	AtomicInteger selection = new AtomicInteger(-1);
	AtomicBoolean holdFail = new AtomicBoolean(false);
	
	Coordinates2D[] targetCenter;
	double[] targetWinSize;
	
	/**
	 * This runs in DefaultEyeSampler thread, since it's called from the sample method.
	 */
	void eyeMonitor(EyeSampler sampler, long sampleLocalTime, int i) {
		if (!sampler.isIn(eyeInstrategy, targetCenter[i], targetWinSize[i])) { // eye is out
			if (!eyeOutEvent[i]) {
				if (!eyeOutStatus[i]) { // first time eye out
					eyeOutLocalTime[i] = sampleLocalTime;
				} else if (localTimeUtil.currentTimeMicros() >= eyeOutLocalTime[i]
						+ targetOutTimeThreshold * 1000 + 0.5) {
					fireEyeOutEvent(i);
					eyeOutEvent[i] = true;
					eyeInEvent[i] = false;
				}
			}
			eyeOutStatus[i] = true;
			eyeInStatus[i] = false;
		} else { // eye is in
			if (!eyeInEvent[i]) {
				if (!eyeInStatus[i]) { // first time eye in
					eyeInLocalTime[i] = sampleLocalTime;
				} else if (localTimeUtil.currentTimeMicros() >= eyeInLocalTime[i]
						+ targetInTimeThreshold * 1000 + 0.5) {
					fireEyeInEvent(i);
					eyeInEvent[i] = true;
					eyeOutEvent[i] = false;
				}
			}
			eyeInStatus[i] = true;
			eyeOutStatus[i] = false;
		}
	}
	
	void fireEyeInEvent(int i) {
		if (startPicking.get()) {
			startPicking.set(false);
			selection.set(i);
		}
	}

	void fireEyeOutEvent(int i) {
		if (checkHolding.get() && i == selection.get()) {
			checkHolding.set(false);
			holdFail.set(true);
		}
	}

	/**
	 * This runs in DefaultEyeSampler thread.
	 */
	public void sample(EyeSampler sampler, long timestamp) {
		if (startPicking.get()) {
			for (int i = 0; i < targetCenter.length; i ++) {
				if (startPicking.get()) {
					eyeMonitor(sampler, timestamp, i);
				}
			}
		} else if (checkHolding.get()) {
			int i = selection.get();
			eyeMonitor(sampler, timestamp, i);
		}
	}

	public void start() {
	}

	public void stop() {
	}

	public boolean waitEyeHold(int which, long timeTarget) {
		if (this.selection.get() != which) {
			return false;
		}
		checkHolding.set(true);
		
		boolean fail = holdFail.get();
		long current = localTimeUtil.currentTimeMicros();
		while ( !fail) {
			if (current >= timeTarget)
				break;
			try {
				Thread.sleep(timeTarget - current > checkInterval ? checkInterval
						: timeTarget - current);
			} catch (InterruptedException e) {
			}
			fail = holdFail.get();
			current = localTimeUtil.currentTimeMicros();
		}
		
		checkHolding.set(false);
		return !fail;
	}
	
	void initEyeMonitor (int nTargets) {
		eyeOutStatus = new boolean[nTargets];
		eyeInStatus = new boolean[nTargets];
		eyeInEvent = new boolean[nTargets];		     
		eyeOutEvent = new boolean[nTargets];
		eyeOutLocalTime = new long[nTargets];
		eyeInLocalTime = new long[nTargets];
		for (int i = 0; i < nTargets; i ++) {
			eyeOutStatus[i] = false;
			eyeInStatus[i] = false;
			eyeInEvent [i] = false;
			eyeOutEvent [i] = false;
		};
	}

	public int waitInitialSelection(Coordinates2D[] targetCenter, double[] targetWinSize, long timeTarget) {
		initEyeMonitor(targetCenter.length);
		
		this.targetCenter = targetCenter;
		this.targetWinSize = targetWinSize;
		selection.set(-1);
		startPicking.set(true);
		holdFail.set(false);
		
		int sel = selection.get();
		long current = localTimeUtil.currentTimeMicros();
		while ( sel < 0) {
			if (current >= timeTarget)
				break;
			try {
				Thread.sleep(timeTarget - current > checkInterval ? checkInterval
						: timeTarget - current);
			} catch (InterruptedException e) {
			}
			sel = selection.get();
			current = localTimeUtil.currentTimeMicros();
		}
		
		startPicking.set(false);
		return sel;
	}

	public int getCheckInterval() {
		return checkInterval;
	}

	public void setCheckInterval(int checkInterval) {
		this.checkInterval = checkInterval;
	}

	public EyeInStrategy getEyeInstrategy() {
		return eyeInstrategy;
	}

	public void setEyeInstrategy(EyeInStrategy eyeInstrategy) {
		this.eyeInstrategy = eyeInstrategy;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public double getTargetOutTimeThreshold() {
		return targetOutTimeThreshold;
	}

	public void setTargetOutTimeThreshold(double targetOutTimeThreshold) {
		this.targetOutTimeThreshold = targetOutTimeThreshold;
	}

	public double getTargetInTimeThreshold() {
		return targetInTimeThreshold;
	}

	public void setTargetInTimeThreshold(double targetInTimeThreshold) {
		this.targetInTimeThreshold = targetInTimeThreshold;
	}
	
	
}
