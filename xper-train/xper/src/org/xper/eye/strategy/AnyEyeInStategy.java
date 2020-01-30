package org.xper.eye.strategy;

import java.util.List;
import java.util.Map;

import org.apache.log4j.Logger;
import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.EyeDevice;

public class AnyEyeInStategy implements EyeInStrategy {
	static Logger logger = Logger.getLogger(AnyEyeInStategy.class);
	
	@Dependency
	List<String> eyeDevices;

	public List<String> getEyeDevices() {
		return eyeDevices;
	}

	public void setEyeDevices(List<String> eyeDevices) {
		this.eyeDevices = eyeDevices;
	}

	public boolean isIn(Map<String, EyeDevice> device, Coordinates2D eyeWinCenter, double eyeWinSize) {
		for (String devId: eyeDevices) {
			if (logger.isDebugEnabled()) {
				logger.debug("Checking " + devId + " for eye in ... (" + eyeWinCenter.getX() + "," + eyeWinCenter.getY() + ") " + eyeWinSize);
			}
			EyeDevice dev = device.get(devId);
			if (dev.isIn(eyeWinCenter, eyeWinSize)) {
				return true;
			}
		}
		return false;
	}

}
