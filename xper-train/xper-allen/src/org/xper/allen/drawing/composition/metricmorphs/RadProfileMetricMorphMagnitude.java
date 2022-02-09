package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.drawing.stick.stickMath_lib;

public class RadProfileMetricMorphMagnitude{
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public double oldValue;
	public double min;
	public double max;
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public double calculateMagnitude() {
		double range = max-min;
		double newValue;
		double outerLowerBound = (oldValue - percentChangeUpperBound*range);
		if(outerLowerBound<min)
			outerLowerBound=min;
		double outerUpperBound = (oldValue + percentChangeUpperBound*range);
		if(outerUpperBound>max) {
			outerUpperBound=max;
		}
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
