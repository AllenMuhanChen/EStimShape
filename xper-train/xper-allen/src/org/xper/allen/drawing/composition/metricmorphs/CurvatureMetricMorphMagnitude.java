package org.xper.allen.drawing.composition.metricmorphs;

import org.xper.drawing.stick.stickMath_lib;

public class CurvatureMetricMorphMagnitude{
	public double percentChangeLowerBound;
	public double oldValue;
	public double range;

	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public double calculateMagnitude(double arcLen) {
		System.out.println("AC6792482: " + oldValue);
		range = arcLen;
		double newValue;


		while (true) {
			if(oldValue < 0.6 * arcLen) {
				range = 0.6 * arcLen;
				double innerUpperBound = (oldValue - percentChangeLowerBound*range);
				double innerLowerBound = (oldValue + percentChangeLowerBound*range);
				newValue = (stickMath_lib.rand01() * 0.4 + 0.2) * arcLen;
				if (newValue < innerUpperBound || newValue > innerLowerBound)
					break;
			}
			else if(oldValue < 6 * arcLen) {
				range = 6 * arcLen - 0.6*arcLen;
				double innerUpperBound = (oldValue - percentChangeLowerBound*range);
				double innerLowerBound = (oldValue + percentChangeLowerBound*range);

				newValue = (stickMath_lib.rand01() * 5.4 + 0.6) * arcLen;
				if (newValue < innerUpperBound || newValue > innerLowerBound)
					break;


			}
			else {
				newValue = (stickMath_lib.rand01() * 5.4 + 0.6) * arcLen;
				return newValue;
			}
			/*
			newValue = stickMath_lib.randDouble(outerLowerBound, outerUpperBound);
			if (newValue < innerUpperBound || newValue > innerLowerBound)
				break;
			 */
		}
		return newValue;

	}

}
