package org.xper.juice;

import org.xper.Dependency;
import org.xper.acq.device.DigitalPortOutDevice;
import org.xper.util.ThreadUtil;

public class DigitalPortJuice implements DynamicJuice {
	
	@Dependency
	DigitalPortOutDevice device;
	@Dependency
	long reward;
	@Dependency
	long triggerDelay = 0;
	
	static long TRIGGER = 128;

	public void setReward(double reward) {
		this.reward = (long)reward;
	}
	
	public void deliver() {
		device.write(new long []{reward});
		ThreadUtil.sleep(triggerDelay);
		device.write(new long []{TRIGGER});
	}

	public long getReward() {
		return reward;
	}

	public DigitalPortOutDevice getDevice() {
		return device;
	}

	public void setDevice(DigitalPortOutDevice device) {
		this.device = device;
	}

	public long getTriggerDelay() {
		return triggerDelay;
	}

	public void setTriggerDelay(long triggerDelay) {
		this.triggerDelay = triggerDelay;
	}
}
