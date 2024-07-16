package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.drawing.stick.stickMath_lib;

public class SizeMetricMorphMagnitude{
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public double newValue;
	public final static double range = 1.0;
	public final static double min = 0.1;

	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C)
	 * @return
	 * @param oldValue
	 */
	public double calculateMagnitude(double oldValue) {
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
		this.newValue = newValue;
		return newValue;
	}

}