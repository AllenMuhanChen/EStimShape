package org.xper.allen.drawing.composition;

import org.xper.drawing.stick.stickMath_lib;

public class MetricMorphMagnitude {
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public double oldValue;
	public double range;
	
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public double calculateMagnitude() {
		double newValue;
		double outterLowerBound = (oldValue - percentChangeUpperBound*range)/2;
		double outterUpperBound = (oldValue + percentChangeUpperBound*range)/2;
		double innerUpperBound = (oldValue - percentChangeLowerBound*range)/2;
		double innerLowerBound = (oldValue + percentChangeLowerBound*range)/2;
		while (true) {
			newValue = stickMath_lib.randDouble(outterLowerBound, outterUpperBound);
			if (newValue < innerUpperBound && newValue > innerLowerBound)
				break;
		}
		return newValue;
	}
	
}
