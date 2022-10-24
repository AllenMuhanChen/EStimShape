package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.drawing.stick.stickMath_lib;

public abstract class MetricMorphMagnitude {
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public double oldValue;
	public double range;
	public double min;
	public double max;
	
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public abstract double calculateMagnitude();
	
}
