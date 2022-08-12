package org.xper.eye;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyePosition;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadHelper;

/**
 * Sample eye signals in its own thread using AcqSamplingDevice. 
 * The thread is started in EyeMonitorController when fixation point in on the screen.
 * It is stopped in EyeMonitorController when the trial stops.
 * 
 * Ask EyeDevice to pull eye signals from the samples.
 * 
 * Fire events to EyeSamplerEventListener. These listeners are started 
 * when the thread starts and stopped when the thread stops.
 * 
 * @author John
 *
 */
public class DefaultEyeSampler implements EyeSampler {
	static Logger logger = Logger.getLogger(DefaultEyeSampler.class);

	@Dependency
	Map<String, EyeDevice> eyeDevice;
	@Dependency
	List<EyeSamplerEventListener> sampleListeners;
	@Dependency
	AcqSamplingDevice acqSamplingDevice;
	@Dependency
	TimeUtil localTimeUtil;

	/**
	 * In milliseconds.
	 */
	@Dependency
	double samplingInterval;


	ThreadHelper threadHelper = new ThreadHelper("DefaultEyeSampler", this);

	public boolean isRunning() {
		return threadHelper.isRunning();
	}

	public void stop() {
		if (isRunning()) {
			threadHelper.stop();
			threadHelper.join();
		}
	}

	public void start() {
		threadHelper.start();
	}

	public void run() {
		try {
			if (logger.isDebugEnabled()) {
				logger.debug("DefaultEyeSampler started.");
			}

			threadHelper.started();
			
			for (EyeSamplerEventListener listener : sampleListeners) {
				listener.start();
			}

			while (!threadHelper.isDone()) {
				long sampleLocalTime = acqSamplingDevice.scan();
				for (EyeDevice dev : eyeDevice.values()) {
					dev.readEyeSignal(acqSamplingDevice);
				}
				
				for (EyeSamplerEventListener listener : sampleListeners) {
					listener.sample(this, sampleLocalTime);
				}

				long sleepTime = (sampleLocalTime
						+ (long) (samplingInterval * 1000) - localTimeUtil
						.currentTimeMicros()) / 1000;
				if (sleepTime > 0) {
					try {
						Thread.sleep(sleepTime);
					} catch (InterruptedException e) {
					}
				}
			}
		} finally {
			if (logger.isDebugEnabled()) {
				logger.debug("DefaultEyeSampler stopped.");
			}
			try {
				for (EyeSamplerEventListener listener : sampleListeners) {
					listener.stop();
				}
				threadHelper.stopped();
			} catch (Exception e) {
				logger.warn(e.getMessage());
				e.printStackTrace();
			}
		}
	}
	
	public boolean isIn(EyeInStrategy strategy, Coordinates2D eyeWinCenter, double eyeWinSize) {
		return strategy.isIn(eyeDevice, eyeWinCenter, eyeWinSize);
	}

	public EyePosition getEyePositions() {
		Map<String, Coordinates2D> eyePos = new HashMap<String, Coordinates2D>();
		for (Map.Entry<String, EyeDevice> ent : eyeDevice.entrySet()) {
			String key = (String) ent.getKey();
			EyeDevice dev = (EyeDevice) ent.getValue();
			eyePos.put(key, dev.getEyePosition());
		}
		return new EyePosition(eyePos);
	}

	public AcqSamplingDevice getAcqSamplingDevice() {
		return acqSamplingDevice;
	}

	public void setAcqSamplingDevice(AcqSamplingDevice acqSamplingDevice) {
		this.acqSamplingDevice = acqSamplingDevice;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

	public double getSamplingInterval() {
		return samplingInterval;
	}

	public void setSamplingInterval(double samplingInterval) {
		this.samplingInterval = samplingInterval;
	}

	public Map<String, EyeDevice> getEyeDevice() {
		return eyeDevice;
	}

	public void setEyeDevice(Map<String, EyeDevice> eyeDevice) {
		this.eyeDevice = eyeDevice;
	}

	public List<EyeSamplerEventListener> getSampleListeners() {
		return sampleListeners;
	}

	public void setSampleListeners(List<EyeSamplerEventListener> sampleListeners) {
		this.sampleListeners = sampleListeners;
	}
}
