package org.xper.allen.drawing.composition.metricmorphs;

import java.util.Collections;
import java.util.LinkedList;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.drawing.stick.stickMath_lib;

public class CurvatureMetricMorphMagnitude{
	public double percentChangeLowerBound;
	public double oldValue;
	public double range;
	public double radView;
	public CurvatureMetricMorphMagnitude(double radView) {
		this.radView = radView;
	}

	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public double calculateMagnitude(AllenMAxisArc inArc) {
		//range = arcLen;
		double newValue;
		//		radView = 5;
		double oldCurvature = 1/oldValue;
		//		while (true) {
		//			
		//			if(oldValue < 0.6 * radView) {
		//				range = 0.6 * radView / 3;
		//				double innerUpperBound = (oldValue - percentChangeLowerBound*range);
		//				double innerLowerBound = (oldValue + percentChangeLowerBound*range);
		//				newValue = (stickMath_lib.rand01() * 0.4 + 0.2) * radView;
		//				if (newValue < innerUpperBound || newValue > innerLowerBound)
		//					break;
		//			}
		//			else if(oldValue < 6 * radView) {
		//				range = (6 * radView - 0.6*radView) / 2;
		//				double innerUpperBound = (oldValue - percentChangeLowerBound*range);
		//				double innerLowerBound = (oldValue + percentChangeLowerBound*range);
		//
		//				newValue = (stickMath_lib.rand01() * 5.4 + 0.6) * radView;
		//				if (newValue < innerUpperBound || newValue > innerLowerBound)
		//					break;
		//
		//
		//			}
		//			else {
		//				newValue = 1 * radView;
		//				return newValue;
		//			}
		//
		//		}

		while (true) {

			if(oldCurvature > 0.5) {
				range = 0.5;
				double innerUpperBound = (oldCurvature - percentChangeLowerBound*range);
				double innerLowerBound = (oldCurvature + percentChangeLowerBound*range);
				double newCurvature = (stickMath_lib.rand01()* range) + 0.5;
				if (newCurvature < innerUpperBound || newCurvature > innerLowerBound) {
					newValue = 1/newCurvature;
					return newValue;
				}

			}
			else if(oldCurvature>0.2 ) {
				range = 0.3;
				double innerUpperBound = (oldCurvature - percentChangeLowerBound*range);
				double innerLowerBound = (oldCurvature + percentChangeLowerBound*range);

				double newCurvature = stickMath_lib.rand01()*range + 0.3;
				if (newCurvature < innerUpperBound || newCurvature > innerLowerBound) {
					newValue = 1/newCurvature;
					return newValue;
				}
			}
			else {
				newValue = 1/0.2;
				return newValue;
			}

		}

		//		while (true) {
		//			newValue = stickMath_lib.randDouble(0,6*radView);
		//			double curvature = 1/newValue;
		//			System.out.println("AC945890534: " + curvature);
		//			//			double aspectRatio = simulateCurvature(inArc, newValue);
		//			//			System.out.println("AC945890534: " + aspectRatio);
		//			if(curvature > 0 && curvature < 0.1) {
		//				return newValue;
		//			}
		//		}

	}

	public static double simulateCurvature(AllenMAxisArc inArc, double newRad) {
		double heightWidthRatio = 0;
		if (newRad>=10000) {
			heightWidthRatio=0;
		} else {
			double angleExtend = inArc.getArcLen()/inArc.getRad();
			double maxStep = inArc.getMaxStep();
			LinkedList<Double> mPtsY = new LinkedList<>();
			LinkedList<Double> mPtsZ = new LinkedList<>();

			for (int step = 1 ; step <=maxStep; step++)
			{
				double nowu = ((double)step-1) / ((double)maxStep-1);
				double now_angle = nowu * angleExtend - 0.5 * angleExtend;

				mPtsY.add(newRad * Math.cos(now_angle));
				mPtsZ.add(newRad * Math.sin(now_angle));
			}


			double height = Collections.max(mPtsY) - Collections.min(mPtsY);
			double width = Collections.max(mPtsZ) - Collections.min(mPtsZ);

			heightWidthRatio = height/width;
		}
		return heightWidthRatio;
	}

}
