package org.xper.allen.drawing.composition.metricmorphs;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class MetricMorphVector {
	public double percentChangeLowerBound;
	public double percentChangeUpperBound;
	public Vector3d oldVector;
	public double range;
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public Vector3d calculateVector() {
		double oldAngle = oldVector.angle(oldVector);
		double outerLowerBound = (oldAngle - percentChangeUpperBound*range);
		double outerUpperBound = (oldAngle + percentChangeUpperBound*range);
		double innerUpperBound = (oldAngle - percentChangeLowerBound*range);
		double innerLowerBound = (oldAngle + percentChangeLowerBound*range);
		Vector3d newVector;
		while (true) {
			newVector = stickMath_lib.randomUnitVec();
			double newAngle = newVector.angle(oldVector);
			if (newAngle > outerLowerBound && newAngle < outerUpperBound)
				if(newAngle < innerUpperBound || newAngle > innerLowerBound)
					break;
		}
		return newVector;
	}
	
}
