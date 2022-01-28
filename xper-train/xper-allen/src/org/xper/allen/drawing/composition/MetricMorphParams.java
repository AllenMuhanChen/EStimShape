package org.xper.allen.drawing.composition;

public class MetricMorphParams{
	public double orientationChance; //chance to change orientation
	public double lengthChance;
	public double radiusChance;
	public double[] orientationMagnitude; //magnitude in random morph (angle-radians bounds)
	public double[] lengthMagnitude; //magnitude in random morph (in percent bounds)
	public double[] radiusMagnitude;
}