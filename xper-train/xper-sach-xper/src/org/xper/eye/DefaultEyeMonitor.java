package org.xper.eye;

import java.util.List;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.listener.EyeEventListener;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyePosition;
import org.xper.eye.win.EyeWindowAdjustable;
import org.xper.eye.win.EyeWindowAlgorithm;
import org.xper.eye.win.EyeWindowMessageListener;
import org.xper.time.TimeUtil;

/**
 * Classical eye monitoring logic. 
 * 
 * Checks eye in and eye out and relay the status information to TrialExperimentEyeController 
 * by firing eye events.
 * 
 * The sample method runs in DefaultEyeSampler thread.
 * 
 * @author John
 *
 */
public class DefaultEyeMonitor implements EyeMonitor, EyeSamplerEventListener, EyeWindowAdjustable {
	static Logger logger = Logger.getLogger(DefaultEyeMonitor.class);

	@Dependency
	List<EyeEventListener> eyeEventListener;
	@Dependency
	EyeInStrategy eyeInstrategy;
	@Dependency
	List<EyeWindowMessageListener> eyeWindowMessageListener;
	
	/**
	 * In degree.
	 * 
	 * FixationCalibration calls setEyeWinCenter in another thread.
	 */
	@Dependency
	AtomicReference<Coordinates2D> eyeWinCenter = new AtomicReference<Coordinates2D>();
	@Dependency
	EyeWindowAlgorithm eyeWindowAlgorithm;
	@Dependency
	TimeUtil localTimeUtil;

	/**
	 * In milliseconds.
	 */
	@Dependency
	double outTimeThreshold;

	/**
	 * In milliseconds.
	 */
	@Dependency
	double inTimeThreshold;
	
	boolean eyeOutStatus;
	boolean eyeInStatus;
	boolean eyeOutEvent;
	boolean eyeInEvent;
	long eyeOutLocalTime;
	long eyeInLocalTime;
	
	public void updateEyeWindow() {
		double eyeWinSize = eyeWindowAlgorithm.getNextEyeWindowSize();
		if (eyeWindowMessageListener != null) {
			for (EyeWindowMessageListener listener : eyeWindowMessageListener) {
				listener.eyeWindowMessage(localTimeUtil.currentTimeMicros(), eyeWinCenter.get(), eyeWinSize);
			}
		}
	}

	/**
	 * This runs in DefaultEyeSampler thread.
	 */
	void fireEyeInEvent(EyePosition eyePos, long timestamp) {
		for (EyeEventListener listener : eyeEventListener) {
			listener.eyeIn(eyePos, timestamp);
		}
	}

	/**
	 * This runs in DefaultEyeSampler thread.
	 */
	void fireEyeOutEvent(EyePosition eyePos, long timestamp) {
		for (EyeEventListener listener : eyeEventListener) {
			listener.eyeOut(eyePos, timestamp);
		}
	}

	public List<EyeEventListener> getEyeEventListener() {
		return eyeEventListener;
	}

	public void setEyeEventListener(List<EyeEventListener> eyeEventListener) {
		this.eyeEventListener = eyeEventListener;
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

	public double getOutTimeThreshold() {
		return outTimeThreshold;
	}

	public void setOutTimeThreshold(double outTimeThreshold) {
		this.outTimeThreshold = outTimeThreshold;
	}

	public double getInTimeThreshold() {
		return inTimeThreshold;
	}

	public void setInTimeThreshold(double inTimeThreshold) {
		this.inTimeThreshold = inTimeThreshold;
	}

	/**
	 * This runs in DefaultEyeSampler thread.
	 */
	public void sample(EyeSampler sampler, long sampleLocalTime) {
		if (!sampler.isIn(eyeInstrategy, eyeWinCenter.get(), eyeWindowAlgorithm.getCurrentEyeWindowSize())) { // eye is out
			if (!eyeOutEvent) {
				if (!eyeOutStatus) { // first time eye out
					eyeOutLocalTime = sampleLocalTime;
				} else if (localTimeUtil.currentTimeMicros() >= eyeOutLocalTime
						+ outTimeThreshold * 1000 + 0.5) {
					fireEyeOutEvent(sampler.getEyePositions(), eyeOutLocalTime);
					eyeOutEvent = true;
					eyeInEvent = false;
				}
			}
			eyeOutStatus = true;
			eyeInStatus = false;
		} else { // eye is in
			if (!eyeInEvent) {
				if (!eyeInStatus) { // first time eye in
					eyeInLocalTime = sampleLocalTime;
				} else if (localTimeUtil.currentTimeMicros() >= eyeInLocalTime
						+ inTimeThreshold * 1000 + 0.5) {
					fireEyeInEvent(sampler.getEyePositions(), eyeInLocalTime);
					eyeInEvent = true;
					eyeOutEvent = false;
				}
			}
			eyeInStatus = true;
			eyeOutStatus = false;
		}
	}

	/**
	 * This is called when DefaultEyeSampler starts.
	 */
	public void start() {
		eyeOutStatus = false;
		eyeInStatus = false;
		eyeInEvent = false;
		eyeOutEvent = false;
	}

	/**
	 * This is called when DefaultEyeSampler stops.
	 */
	public void stop() {
	}

	public Coordinates2D getEyeWinCenter() {
		return eyeWinCenter.get();
	}

	public void setEyeWinCenter(Coordinates2D eyeWinCenter) {
		this.eyeWinCenter.set(eyeWinCenter);
	}

	public EyeWindowAlgorithm getEyeWindowAlgorithm() {
		return eyeWindowAlgorithm;
	}

	public void setEyeWindowAlgorithm(EyeWindowAlgorithm eyeWindowAlgorithm) {
		this.eyeWindowAlgorithm = eyeWindowAlgorithm;
	}

	public List<EyeWindowMessageListener> getEyeWindowMessageListener() {
		return eyeWindowMessageListener;
	}

	public void setEyeWindowMessageListener(
			List<EyeWindowMessageListener> eyeWindowMessageListener) {
		this.eyeWindowMessageListener = eyeWindowMessageListener;
	}
}
