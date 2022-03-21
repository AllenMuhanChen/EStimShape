package org.xper.allen.drawing.composition.metricmorphs;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class MetricMorphVector {
	public double angleChangeLowerBound;
	public double angleChangeUpperBound;
	public Vector3d oldVector;
	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public Vector3d calculateVector() {
		//The below is putting bounds on the angle difference between the old vector and new vector
		double outerLowerBound = angleChangeLowerBound;
		double outerUpperBound = angleChangeUpperBound;
		Vector3d newVector;
		while (true) {
			newVector = stickMath_lib.randomUnitVec();
			double angleDiff = newVector.angle(oldVector);
			if (angleDiff > outerLowerBound && angleDiff < outerUpperBound)
				break;
		}
		return newVector;
	}
	
}
