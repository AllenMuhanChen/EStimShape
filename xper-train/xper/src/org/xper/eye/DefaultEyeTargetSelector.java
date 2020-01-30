package org.xper.eye;

import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.time.TimeUtil;


public class DefaultEyeTargetSelector implements EyeSamplerEventListener, EyeTargetSelector {

	/**
	 * Interval in ms between successive eye signal check.
	 */
	@Dependency
	int checkInterval = 10;
	@Dependency
	EyeInStrategy eyeInstrategy;
	@Dependency
	TimeUtil localTimeUtil;
	
	AtomicBoolean startPicking = new AtomicBoolean(false);
	AtomicBoolean checkHolding = new AtomicBoolean(false);
	AtomicInteger selection = new AtomicInteger(-1);
	AtomicBoolean holdFail = new AtomicBoolean(false);
	
	Coordinates2D[] targetCenter;
	double[] targetWinSize;
	
	public void sample(EyeSampler sampler, long timestamp) {
		if (startPicking.get()) {
			for (int i = 0; i < targetCenter.length; i ++) {
				if (sampler.isIn(eyeInstrategy, targetCenter[i], targetWinSize[i])) {
					startPicking.set(false);
					selection.set(i);
					break;
				}
			}
		} else if (checkHolding.get()) {
			int i = selection.get();
			if (!sampler.isIn(eyeInstrategy, targetCenter[i], targetWinSize[i])) {
				checkHolding.set(false);
				holdFail.set(true);
			}
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

	public int waitInitialSelection(Coordinates2D[] targetCenter, double[] targetWinSize, long timeTarget) {
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
	
	
}
