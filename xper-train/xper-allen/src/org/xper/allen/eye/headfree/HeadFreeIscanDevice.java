package org.xper.allen.eye.headfree;

import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.IscanDevice;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.eye.zero.EyeZeroMessageListener;

public class HeadFreeIscanDevice extends IscanDevice implements HeadFreeEyeZeroAdjustable{
	@Dependency
	private
	HeadFreeEyeZeroAlgorithm eyeZeroAlgorithm;
	public void readEyeSignal(AcqSamplingDevice dev) {
		getVoltage().setX(dev.getData(getChannel().getX()));
		getVoltage().setY(dev.getData(getChannel().getY()));

		getDegree().set(getMappingAlgorithm().volt2Degree(getVoltage(), getEyeZero()));

		if (getEyeDeviceMessageListener() != null) {
			long tstamp = getLocalTimeUtil().currentTimeMicros();
			for (EyeDeviceMessageListener listener : getEyeDeviceMessageListener()) {
				listener.eyeDeviceMessage(tstamp, getId(), getVoltage(), getDegree().get());
			}
		}

		// collect eye zero signal
		if (getEyeZeroUpdateEnabled().get()) {
			if (isIn(getEyeZeroAlgorithm().getEyeZeroUpdateEyeWinCenter(), getEyeZeroAlgorithm().getEyeZeroUpdateEyeWinThreshold())) {
				getEyeZeroAlgorithm().collectEyeZeroSignal(getVoltage());
			}
			if(isIn(getEyeZeroAlgorithm().getEyeZeroUpdateEyeWinCenter(), getEyeZeroAlgorithm().getEyeZeroInnerThreshold())) {
				getEyeZeroAlgorithm().collectEyeZeroInnerSignal(getVoltage());
			}
		}
	}
	
	public void calculateNewEyeZero() {
		Coordinates2D z = getEyeZeroAlgorithm().getNewEyeZero();

		if (z != null) {
			setEyeZero(z);	
			System.out.println("AC8484932: newEyeZero = "+z.getX() + ", "+z.getY());
		}
		if (getEyeZeroMessageListener() != null) {
			for (EyeZeroMessageListener listener : getEyeZeroMessageListener()) {
				listener.eyeZeroMessage(getLocalTimeUtil().currentTimeMicros(), getId(), getEyeZero());
			}
		}
	}


	public void startEyeZeroInnerSignalCollection() {
		eyeZeroAlgorithm.startInnerEyeZeroSignalCollection();
	}

	public void stopEyeZeroInnerSignalCollection() {
		eyeZeroAlgorithm.stopEyeZeroSignalCollection();
	}


	public HeadFreeEyeZeroAlgorithm getEyeZeroAlgorithm() {
		return eyeZeroAlgorithm;
	}
	public void setEyeZeroAlgorithm(HeadFreeEyeZeroAlgorithm eyeZeroAlgorithm) {
		this.eyeZeroAlgorithm = eyeZeroAlgorithm;
	}


}

