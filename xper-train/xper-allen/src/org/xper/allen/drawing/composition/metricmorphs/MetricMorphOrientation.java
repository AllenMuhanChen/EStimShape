package org.xper.allen.drawing.composition.metricmorphs;

import java.util.ArrayList;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class MetricMorphOrientation {
	public static final double RAD = Math.PI/180;
	private double angleChangeLowerBound;
	private double angleChangeUpperBound;
	private Vector3d oldVector;


	public MetricMorphOrientation() {

	}

	/**
	 * outterLowerBound < innerUpperBound < innerLowerBound < outerUpperBound
	 * A < B < C < D
	 * output can be between (A & B) or (C & D) but NOT (B & C) 
	 * @return
	 */
	public Vector3d calculateVector() {
		Vector3d newVector;

		if(checkInCanonicalBoundary(getOldVector())) {
			newVector = getOldVector();
		} else {
			while (true) {
				newVector = stickMath_lib.randomUnitVec();
				if(checkNewVector(newVector))
					break;
			}
		}
//		newVector = new Vector3d(0,1,0); //sometimes up, sometimes down. Idk why.
		return newVector;
	}

	private boolean checkNewVector(Vector3d newVector) {
		boolean passedCanonicalCheck = !checkInCanonicalBoundary(newVector);
		boolean passedQuadrantCheck = checkInSameQuadrant(newVector);
		boolean passedAngleDiffCheck = checkAngleDiff(newVector);

		return passedCanonicalCheck&&passedAngleDiffCheck&&passedQuadrantCheck;
	}

	/**
	 * Check if new vector is far away enough from oldVector (and not too far)
	 * @param newVector
	 * @return
	 */
	private boolean checkAngleDiff(Vector3d newVector) {
		double outerLowerBound = getAngleChangeLowerBound();
		double outerUpperBound = getAngleChangeUpperBound();
		double angleDiff = newVector.angle(getOldVector());
		if (angleDiff > outerLowerBound && angleDiff < outerUpperBound)
			return true;
		else
			return false;
	}
	
	/**
	 * Check if vector changes quadrants (passes a canonical boundary)
	 * @param newVector
	 * @return
	 */
	private boolean checkInSameQuadrant(Vector3d newVector) {
		boolean oldXSign = isPositive(getOldVector().getX());
		boolean oldYSign = isPositive(getOldVector().getY());
		boolean oldZSign = isPositive(getOldVector().getZ());
		if(isPositive(newVector.getX())==oldXSign){
			if(isPositive(newVector.getY())==oldYSign) {
				if(isPositive(newVector.getZ())==oldZSign) {
					return true;
				}
			}

		}
		return false;
	}
	/**
	 * Checks if vector within a certain degree region from canonical boundaries
	 * @param num
	 * @return
	 */
	private boolean checkInCanonicalBoundary(Vector3d vector) {
		final double DEVIATION = 25*RAD;
		List<Vector3d>canonicalBoundaries = new ArrayList<Vector3d>();
		canonicalBoundaries.add(new Vector3d(1,0,0));
		canonicalBoundaries.add(new Vector3d(-1,0,0));
		canonicalBoundaries.add(new Vector3d(0,1,0));
		canonicalBoundaries.add(new Vector3d(0,-1,0));
		canonicalBoundaries.add(new Vector3d(0,0,1));
		canonicalBoundaries.add(new Vector3d(0,0,-1));

		for(int i=0; i<canonicalBoundaries.size(); i++) {
			double angleDiff = vector.angle(canonicalBoundaries.get(i));
			if(angleDiff<DEVIATION) {
				return true;
			}
		}
		return false;
	}

	public static boolean isPositive(double num) {
		if(num>0) {
			return true;
		}
		else {
			return false;
		}
	}

	public Vector3d getOldVector() {
		return oldVector;
	}

	public void setOldVector(Vector3d oldVector) {
		this.oldVector = oldVector;
	}

	public double getAngleChangeUpperBound() {
		return angleChangeUpperBound;
	}

	public void setAngleChangeUpperBound(double angleChangeUpperBound) {
		this.angleChangeUpperBound = angleChangeUpperBound;
	}

	public double getAngleChangeLowerBound() {
		return angleChangeLowerBound;
	}

	public void setAngleChangeLowerBound(double angleChangeLowerBound) {
		this.angleChangeLowerBound = angleChangeLowerBound;
	}

}
