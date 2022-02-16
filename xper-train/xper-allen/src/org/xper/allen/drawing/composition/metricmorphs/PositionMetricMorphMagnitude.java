package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.drawing.stick.stickMath_lib;

public class PositionMetricMorphMagnitude{
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public double oldValue;
	public final static double min = 1;
	public final static double max = 51;
	private final static double range = max-min;
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public int calculateMagnitude() {
		double newValue;
		double outerLowerBound = (oldValue - percentChangeUpperBound*range);
		if(outerLowerBound < min)
			outerLowerBound = min;
		double outerUpperBound = (oldValue + percentChangeUpperBound*range);
		if(outerUpperBound < max)
			outerUpperBound = max;
		double innerUpperBound = (oldValue - percentChangeLowerBound*range);
		double innerLowerBound = (oldValue + percentChangeLowerBound*range);
		while (true) {
			newValue = stickMath_lib.randDouble(outerLowerBound, outerUpperBound);
			if (newValue < innerUpperBound || newValue > innerLowerBound)
				break;
		}
		return (int) Math.round(newValue);
	}
	
}
