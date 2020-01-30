package org.xper.eye.strategy;

import java.util.Map;

import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.EyeDevice;


public class MonoEyeInStrategy implements EyeInStrategy {
	@Dependency
	String eyeDeviceId;

	public boolean isIn(Map<String, EyeDevice> device, Coordinates2D eyeWinCenter, double eyeWinSize) {
		EyeDevice dev = device.get(eyeDeviceId);
		return dev.isIn(eyeWinCenter, eyeWinSize);
	}

	public String getEyeDeviceId() {
		return eyeDeviceId;
	}

	public void setEyeDeviceId(String eyeDeviceId) {
		this.eyeDeviceId = eyeDeviceId;
	}

}
