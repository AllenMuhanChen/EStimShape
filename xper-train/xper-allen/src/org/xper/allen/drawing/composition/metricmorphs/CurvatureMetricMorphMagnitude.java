package org.xper.allen.drawing.composition.metricmorphs;

import java.util.Collections;
import java.util.LinkedList;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.drawing.stick.stickMath_lib;

public class CurvatureMetricMorphMagnitude{
	private double percentChangeLowerBound;
	private double oldValue;
	private double range;
	private double radView;
	public CurvatureMetricMorphMagnitude(double radView) {
		this.radView = radView;
	}


	public double calculateMagnitude(AllenMAxisArc inArc) {
		double newValue;
		double oldCurvature = 1/oldValue;

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
				newValue = oldValue;
			}
		}
	}

//	private static double simulateCurvature(AllenMAxisArc inArc, double newRad) {
//		double heightWidthRatio = 0;
//		if (newRad>=10000) {
//			heightWidthRatio=0;
//		} else {
//			double angleExtend = inArc.getArcLen()/inArc.getRad();
//			double maxStep = inArc.getMaxStep();
//			LinkedList<Double> mPtsY = new LinkedList<>();
//			LinkedList<Double> mPtsZ = new LinkedList<>();
//
//			for (int step = 1 ; step <=maxStep; step++)
//			{
//				double nowu = ((double)step-1) / ((double)maxStep-1);
//				double now_angle = nowu * angleExtend - 0.5 * angleExtend;
//
//				mPtsY.add(newRad * Math.cos(now_angle));
//				mPtsZ.add(newRad * Math.sin(now_angle));
//			}
//
//
//			double height = Collections.max(mPtsY) - Collections.min(mPtsY);
//			double width = Collections.max(mPtsZ) - Collections.min(mPtsZ);
//
//			heightWidthRatio = height/width;
//		}
//		return heightWidthRatio;
//	}

	public double getRadView() {
		return radView;
	}

	public void setRadView(double radView) {
		this.radView = radView;
	}

	public double getRange() {
		return range;
	}

	public void setRange(double range) {
		this.range = range;
	}

	public double getOldValue() {
		return oldValue;
	}

	public void setOldValue(double oldValue) {
		this.oldValue = oldValue;
	}

	public double getPercentChangeLowerBound() {
		return percentChangeLowerBound;
	}

	public void setPercentChangeLowerBound(double percentChangeLowerBound) {
		this.percentChangeLowerBound = percentChangeLowerBound;
	}

}
