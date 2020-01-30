package org.xper.eye.listener;

import org.xper.drawing.Coordinates2D;

public interface EyeDeviceMessageListener {
	public void eyeDeviceMessage(long timestamp, String id, Coordinates2D volt, Coordinates2D degree);
}
