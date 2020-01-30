package org.xper.eye;

import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.vo.EyeDeviceChannelSpec;
import org.xper.eye.zero.EyeZeroAdjustable;
import org.xper.eye.zero.EyeZeroAlgorithm;
import org.xper.eye.zero.EyeZeroMessageListener;
import org.xper.time.TimeUtil;

public class IscanDevice implements EyeDevice, EyeZeroAdjustable {
	static Logger logger = Logger.getLogger(IscanDevice.class);

	/**
	 * In volts.
	 */
	@Dependency
	Coordinates2D eyeZero;
	@Dependency
	EyeDeviceChannelSpec channel;
	@Dependency
	MappingAlgorithm mappingAlgorithm;
	@Dependency
	EyeZeroAlgorithm eyeZeroAlgorithm;
	@Dependency
	AtomicBoolean eyeZeroUpdateEnabled = new AtomicBoolean(false);
	@Dependency
	String id;
	@Dependency
	List<EyeDeviceMessageListener> eyeDeviceMessageListener;
	@Dependency
	List<EyeZeroMessageListener> eyeZeroMessageListener;
	@Dependency
	TimeUtil localTimeUtil;

	Coordinates2D voltage = new Coordinates2D();
	AtomicReference<Coordinates2D> degree = new AtomicReference<Coordinates2D>();

	public boolean isIn(Coordinates2D eyeWinCenter, double eyeWinSize) {
		if (logger.isDebugEnabled()) {
			logger.debug(id + " - eyeWinSize: " + eyeWinSize + " eyeWinCenter: ("
					+ eyeWinCenter.getX() + "," + eyeWinCenter.getY()
					+ ") eyePosition: (" + getEyePosition().getX() + ","
					+ getEyePosition().getY() + ")");
		}
		double dx = getEyePosition().getX() - eyeWinCenter.getX();
		double dy = getEyePosition().getY() - eyeWinCenter.getY();
		return (dx * dx + dy * dy) <= eyeWinSize * eyeWinSize;
	}

	public void readEyeSignal(AcqSamplingDevice dev) {
		voltage.setX(dev.getData(channel.getX()));
		voltage.setY(dev.getData(channel.getY()));

		degree.set(mappingAlgorithm.volt2Degree(voltage, eyeZero));
		
		if (eyeDeviceMessageListener != null) {
			long tstamp = localTimeUtil.currentTimeMicros();
			for (EyeDeviceMessageListener listener : eyeDeviceMessageListener) {
				listener.eyeDeviceMessage(tstamp, id, voltage, degree.get());
			}
		}

		// collect eye zero signal
		if (eyeZeroUpdateEnabled.get()) {
			if (logger.isDebugEnabled()) {
				logger.debug("Checking " + id + " for eye zero update...");
			}
			if (isIn(eyeZeroAlgorithm.getEyeZeroUpdateEyeWinCenter(), eyeZeroAlgorithm.getEyeZeroUpdateEyeWinThreshold())) {
				eyeZeroAlgorithm.collectEyeZeroSignal(voltage);
			}
		}
	}

	public EyeDeviceChannelSpec getChannel() {
		return channel;
	}

	public void setChannel(EyeDeviceChannelSpec channel) {
		this.channel = channel;
	}

	public Coordinates2D getEyeZero() {
		return eyeZero;
	}

	public void setEyeZero(Coordinates2D eyeZero) {
		this.eyeZero = eyeZero;
	}

	public Coordinates2D getEyePosition() {
		return degree.get();
	}

	void setEyePosition(Coordinates2D newPos) {
		degree.set(newPos);
	}

	public void calculateNewEyeZero() {
		Coordinates2D z = eyeZeroAlgorithm.getNewEyeZero();
		if (z != null) {
			eyeZero = z;	
		}
		if (eyeZeroMessageListener != null) {
			for (EyeZeroMessageListener listener : eyeZeroMessageListener) {
				listener.eyeZeroMessage(localTimeUtil.currentTimeMicros(), id, eyeZero);
			}
		}
	}

	public void startEyeZeroSignalCollection() {
		eyeZeroAlgorithm.startEyeZeroSignalCollection();
	}

	public void stopEyeZeroSignalCollection() {
		eyeZeroAlgorithm.stopEyeZeroSignalCollection();
	}

	public boolean isEyeZeroUpdateEnabled() {
		return eyeZeroUpdateEnabled.get();
	}

	public void setEyeZeroUpdateEnabled(boolean eyeZeroUpdateEnabled) {
		this.eyeZeroUpdateEnabled.set(eyeZeroUpdateEnabled);
	}

	public MappingAlgorithm getMappingAlgorithm() {
		return mappingAlgorithm;
	}

	public void setMappingAlgorithm(MappingAlgorithm mappingAlgorithm) {
		this.mappingAlgorithm = mappingAlgorithm;
	}

	public EyeZeroAlgorithm getEyeZeroAlgorithm() {
		return eyeZeroAlgorithm;
	}

	public void setEyeZeroAlgorithm(EyeZeroAlgorithm eyeZeroAlgorithm) {
		this.eyeZeroAlgorithm = eyeZeroAlgorithm;
	}

	public String getId() {
		return id;
	}

	public void setId(String id) {
		this.id = id;
	}

	public List<EyeDeviceMessageListener> getEyeDeviceMessageListener() {
		return eyeDeviceMessageListener;
	}

	public void setEyeDeviceMessageListener(
			List<EyeDeviceMessageListener> eyeDeviceMessageListener) {
		this.eyeDeviceMessageListener = eyeDeviceMessageListener;
	}

	public List<EyeZeroMessageListener> getEyeZeroMessageListener() {
		return eyeZeroMessageListener;
	}

	public void setEyeZeroMessageListener(
			List<EyeZeroMessageListener> eyeZeroMessageListener) {
		this.eyeZeroMessageListener = eyeZeroMessageListener;
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}
	
	
}
