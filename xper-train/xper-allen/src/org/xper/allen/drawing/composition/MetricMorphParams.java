package org.xper.allen.drawing.composition;

public class MetricMorphParams{
	public boolean orientationFlag; //change orientation?
	public boolean rotationFlag;
	public boolean lengthFlag;
	public boolean sizeFlag;
	public boolean curvatureFlag;
	public boolean positionFlag;
	public boolean radProfileFlag;
	public double[] orientationMagnitude; //magnitude in random morph (angle-radians bounds)
	public double[] lengthMagnitude; //magnitude in random morph (in percent bounds)
	public double[] radiusMagnitude;
}