package org.xper.eye.win;

import org.xper.drawing.Coordinates2D;

public interface EyeWindowMessageListener {
	public void eyeWindowMessage(long timestamp, Coordinates2D center, double size);
}
