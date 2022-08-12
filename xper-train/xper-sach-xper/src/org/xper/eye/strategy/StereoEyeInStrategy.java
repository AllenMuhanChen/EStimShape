package org.xper.eye.strategy;

import java.util.Map;

import org.xper.Dependency;
import org.xper.drawing.Coordinates2D;
import org.xper.eye.EyeDevice;


public class StereoEyeInStrategy implements EyeInStrategy {
	@Dependency
	String leftDeviceId;
	@Dependency
	String rightDeviceId;

	public boolean isIn(Map<String, EyeDevice> device, Coordinates2D eyeWinCenter, double eyeWinSize) {
		EyeDevice left = device.get(leftDeviceId);
		EyeDevice right = device.get(rightDeviceId);
		if (left.isIn(eyeWinCenter, eyeWinSize) && right.isIn(eyeWinCenter, eyeWinSize)) {
			return true;
		} else {
			return false;
		}
	}

	public String getLeftDeviceId() {
		return leftDeviceId;
	}

	public void setLeftDeviceId(String leftDeviceId) {
		this.leftDeviceId = leftDeviceId;
	}

	public String getRightDeviceId() {
		return rightDeviceId;
	}

	public void setRightDeviceId(String rightDeviceId) {
		this.rightDeviceId = rightDeviceId;
	}
}
