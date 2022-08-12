package org.xper.acq.mock;

import org.xper.Dependency;
import org.xper.acq.device.AcqSamplingDevice;
import org.xper.time.TimeUtil;

public class EmptySamplingDevice implements AcqSamplingDevice {
	@Dependency
	TimeUtil localTimeUtil;

	public double getData(int channel) {
		return 0;
	}

	public long scan() {
		return localTimeUtil.currentTimeMicros();
	}

	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}

}
