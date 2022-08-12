package org.xper.eye.win;

import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicReference;

import org.xper.Dependency;


public class RampEyeWindowAlgorithm implements EyeWindowAlgorithm {
	@Dependency
	double baseWindowSize;
	@Dependency
	int rampLength;
	@Dependency
	double initialWindowSize;

	AtomicLong index = new AtomicLong(0);	
	AtomicReference<Double> currentEyeWinSize = new AtomicReference<Double>();
	
	public void init() {
		this.currentEyeWinSize.set(initialWindowSize);
	}

	public double getNextEyeWindowSize() {
		long i = index.incrementAndGet();
		double s;
		if (i >= rampLength) {
			s = baseWindowSize;
		} else {
			s = initialWindowSize * (double)(rampLength - i) / (double)rampLength
					+ baseWindowSize * (double)i / (double)rampLength;
		}
		currentEyeWinSize.set(s);
		return s;
	}
	
	/**
	 * This may be called from a thread other than the eye monitoring thread to reset the eye window size.
	 */
	public void resetEyeWindowSize() {
		index.set(0);
	}

	public double getBaseWindowSize() {
		return baseWindowSize;
	}

	public void setBaseWindowSize(double baseWindowSize) {
		this.baseWindowSize = baseWindowSize;
	}

	public int getRampLength() {
		return rampLength;
	}

	public void setRampLength(int rampLength) {
		this.rampLength = rampLength;
	}

	public double getInitialWindowSize() {
		return initialWindowSize;
	}

	public void setInitialWindowSize(double initialWindowSize) {
		this.initialWindowSize = initialWindowSize;
	}

	public double getCurrentEyeWindowSize() {
		return currentEyeWinSize.get();
	}

}
