package org.xper.eye.zero;

import org.xper.drawing.Coordinates2D;

public interface EyeZeroMessageListener {
	public void eyeZeroMessage(long timestamp, String id, Coordinates2D zero);
}
