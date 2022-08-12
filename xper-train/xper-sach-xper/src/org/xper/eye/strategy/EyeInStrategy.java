package org.xper.eye.strategy;

import java.util.Map;

import org.xper.drawing.Coordinates2D;
import org.xper.eye.EyeDevice;


public interface EyeInStrategy {
	public boolean isIn(Map<String, EyeDevice> device, Coordinates2D eyeWinCenter, double eyeWinSize);
}
