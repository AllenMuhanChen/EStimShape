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
	private
	Coordinates2D eyeZero;
	@Dependency
	private
	EyeDeviceChannelSpec channel;
	@Dependency
	private
	MappingAlgorithm mappingAlgorithm;
	@Dependency
	private
	EyeZeroAlgorithm eyeZeroAlgorithm;
	@Dependency
	private
	AtomicBoolean eyeZeroUpdateEnabled = new AtomicBoolean(false);
	@Dependency
	String id;
	@Dependency
	List<EyeDeviceMessageListener> eyeDeviceMessageListener;
	@Dependency
	protected
	List<EyeZeroMessageListener> eyeZeroMessageListener;
	@Dependency
	TimeUtil localTimeUtil;

	private Coordinates2D voltage = new Coordinates2D();
	private AtomicReference<Coordinates2D> degree = new AtomicReference<Coordinates2D>();

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
		getVoltage().setX(dev.getData(getChannel().getX()));
		getVoltage().setY(dev.getData(getChannel().getY()));

		getDegree().set(getMappingAlgorithm().volt2Degree(getVoltage(), getEyeZero()));
		
		if (eyeDeviceMessageListener != null) {
			long tstamp = localTimeUtil.currentTimeMicros();
			for (EyeDeviceMessageListener listener : eyeDeviceMessageListener) {
				listener.eyeDeviceMessage(tstamp, id, getVoltage(), getDegree().get());
			}
		}

		// collect eye zero signal
		if (getEyeZeroUpdateEnabled().get()) {
			if (logger.isDebugEnabled()) {
				logger.debug("Checking " + id + " for eye zero update...");
			}
			if (isIn(getEyeZeroAlgorithm().getEyeZeroUpdateEyeWinCenter(), getEyeZeroAlgorithm().getEyeZeroUpdateEyeWinThreshold())) {
				getEyeZeroAlgorithm().collectEyeZeroSignal(getVoltage());
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
		return getDegree().get();
	}

	void setEyePosition(Coordinates2D newPos) {
		getDegree().set(newPos);
	}

	public void calculateNewEyeZero() {
		Coordinates2D z = getEyeZeroAlgorithm().getNewEyeZero();

		if (z != null) {
			setEyeZero(z);	
			System.out.println("IscanDevice: newEyeZero = "+z.getX() + ", "+z.getY());
		}
		if (eyeZeroMessageListener != null) {
			for (EyeZeroMessageListener listener : eyeZeroMessageListener) {
				listener.eyeZeroMessage(localTimeUtil.currentTimeMicros(), id, getEyeZero());
			}
		}
	}

	public void startEyeZeroSignalCollection() {
		getEyeZeroAlgorithm().startEyeZeroSignalCollection();
	}

	public void stopEyeZeroSignalCollection() {
		getEyeZeroAlgorithm().stopEyeZeroSignalCollection();
	}

	public boolean isEyeZeroUpdateEnabled() {
		return getEyeZeroUpdateEnabled().get();
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

	protected Coordinates2D getVoltage() {
		return voltage;
	}

	protected void setVoltage(Coordinates2D voltage) {
		this.voltage = voltage;
	}

	protected AtomicReference<Coordinates2D> getDegree() {
		return degree;
	}

	void setDegree(AtomicReference<Coordinates2D> degree) {
		this.degree = degree;
	}

	public AtomicBoolean getEyeZeroUpdateEnabled() {
		return eyeZeroUpdateEnabled;
	}

	public void setEyeZeroUpdateEnabled(AtomicBoolean eyeZeroUpdateEnabled) {
		this.eyeZeroUpdateEnabled = eyeZeroUpdateEnabled;
	}
	
	
}
