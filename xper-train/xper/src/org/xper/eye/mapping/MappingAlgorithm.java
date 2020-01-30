package org.xper.eye.mapping;

import org.xper.drawing.Coordinates2D;


public interface MappingAlgorithm {
	public Coordinates2D volt2Degree (Coordinates2D volt, Coordinates2D eyeZero);
	public Coordinates2D degree2Volt (Coordinates2D degree, Coordinates2D eyeZero);
}
