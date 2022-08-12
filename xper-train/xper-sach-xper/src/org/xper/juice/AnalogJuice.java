package org.xper.juice;

import org.xper.Dependency;
import org.xper.acq.device.AnalogOutDevice;
import org.xper.time.TimeUtil;
import org.xper.util.ThreadUtil;

public class AnalogJuice implements DynamicJuice  {
	@Dependency
	AnalogOutDevice device;
	
	/**
	 * in millisecond
	 */ 
	@Dependency
	double delay;
	@Dependency
	double reward;
	@Dependency
	double bonusDelay;
	@Dependency
	double bonusProbability;
	@Dependency
	TimeUtil localTimeUtil;
	
	static final double ON_VOLT = 5;
	static final double OFF_VOLT = 0;

	public void deliver() {
		ThreadUtil.sleepUtil((long)(localTimeUtil.currentTimeMicros() + delay * 1000 + 0.5), localTimeUtil);
		turnOnJuice();
		ThreadUtil.sleepUtil((long)(localTimeUtil.currentTimeMicros() + reward * 1000 + 0.5), localTimeUtil);
		turnOffJuice();
		if (bonusProbability >= Math.random()) {
			ThreadUtil.sleepUtil((long)(localTimeUtil.currentTimeMicros() + bonusDelay * 1000 + 0.5), localTimeUtil);
			turnOnJuice();
			ThreadUtil.sleepUtil((long)(localTimeUtil.currentTimeMicros() + reward * 1000 + 0.5), localTimeUtil);
			turnOffJuice();
		}
	}
	
	void turnOnJuice () {
		device.write(new double[]{ON_VOLT});
	}
	void turnOffJuice () {
		device.write(new double[]{OFF_VOLT});
	}

	public void setReward(double reward) {
		this.reward = reward;
	}

	public double getDelay() {
		return delay;
	}

	public void setDelay(double delay) {
		this.delay = delay;
	}

	public double getBonusDelay() {
		return bonusDelay;
	}

	public void setBonusDelay(double bonusDelay) {
		this.bonusDelay = bonusDelay;
	}

	public double getBonusProbability() {
		return bonusProbability;
	}

	public void setBonusProbability(double bonusProbability) {
		this.bonusProbability = bonusProbability;
	}

	public double getReward() {
		return reward;
	}

	public AnalogOutDevice getDevice() {
		return device;
	}

	public void setDevice(AnalogOutDevice device) {
		this.device = device;
	}
	
	public TimeUtil getLocalTimeUtil() {
		return localTimeUtil;
	}

	public void setLocalTimeUtil(TimeUtil localTimeUtil) {
		this.localTimeUtil = localTimeUtil;
	}
	
}
