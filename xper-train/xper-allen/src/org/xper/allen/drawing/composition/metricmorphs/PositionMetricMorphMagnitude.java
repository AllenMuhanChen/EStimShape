package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.drawing.stick.stickMath_lib;

public class PositionMetricMorphMagnitude{
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public double oldValue;
	public double range;
	public final static double min = 0;
	
	public PositionMetricMorphMagnitude(double range) {
		this.range = range;
	}
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public double calculateMagnitude() {
		double newValue;
		double outerLowerBound = (oldValue - percentChangeUpperBound*range);
		if(outerLowerBound < min)
			outerLowerBound = min;
		double outerUpperBound = (oldValue + percentChangeUpperBound*range);
		double innerUpperBound = (oldValue - percentChangeLowerBound*range);
		double innerLowerBound = (oldValue + percentChangeLowerBound*range);
		while (true) {
			newValue = stickMath_lib.randDouble(outerLowerBound, outerUpperBound);
			if (newValue < innerUpperBound || newValue > innerLowerBound)
				break;
		}
		return newValue;
	}
	
}
