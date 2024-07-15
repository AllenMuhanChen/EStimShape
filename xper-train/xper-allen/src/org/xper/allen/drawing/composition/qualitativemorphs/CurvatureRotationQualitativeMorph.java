package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.drawing.stick.stickMath_lib;

public class CurvatureRotationQualitativeMorph extends QualitativeMorph{
	private boolean curvatureFlag = false;
	private boolean rotationFlag = false;

	private double oldCurvature;
	private double oldRotation;

	private double newCurvature;
	private double newRotation;

	public List<Bin<Double>> curvatureBins;
	public ArrayList<Bin<Double>> scaledCurvatureBins;

	private int assignedCurvatureBin;
	private int assignedRotationBin;

	private boolean is180RotationOkay;

	public double CHANCE_TO_CHANGE_ROTATION_NOT_CURVATURE = 0.5;

	public CurvatureRotationQualitativeMorph() {
		curvatureBins = new ArrayList<Bin<Double>>();
		//scaledCurvatureBins = new ArrayList<>();
	}

	public void loadParams(double oldCurvature, double oldRotation) {
		setOldCurvature(oldCurvature);
		setOldRotation(oldRotation);

		curvatureFlag = false;
		rotationFlag = false;
	}

	public void calculate(AllenMAxisArc inArc) {
		checkIf180RotationOkay(inArc);
		assignBins();

		//curvatureFlag = false; //DEBUG
		if(curvatureFlag) {
			newCurvature = newValueFromBins(scaledCurvatureBins, assignedCurvatureBin);
		}
		else {
			newCurvature = oldCurvature;
		}


		//rotationFlag = true; //DEBUG
		if(rotationFlag) {
			//If the curvature is facing too much towards the viewer or away, rotate by 90 degrees
			if(!is180RotationOkay) {
				if(stickMath_lib.rand01()<0.5)
					newRotation = oldRotation - 90 * Math.PI/180;
				else
					newRotation = oldRotation + 90 * Math.PI/180;

			}
			else { //The rotation should be salient with a 180 rotation
				if(stickMath_lib.rand01()<0.5)
					newRotation = oldRotation - 180 * Math.PI/180;
				else
					newRotation = oldRotation + 180 * Math.PI/180;
			}
		}
		else {
			newRotation = oldRotation;
		}

	}

	private void checkIf180RotationOkay(AllenMAxisArc inArc) {
		Vector3d normal = inArc.normal;
		double[] normalAngles = vector2Angles(normal); //in spherical coords
		double zDirectionNormalAngle = normalAngles[1];
		double[] prohibitedNormalAngles= {-180 * Math.PI/180, 0, 180 * Math.PI/180, 360 * Math.PI/180};
		double tolerance = 25 * Math.PI/180;

		boolean isOkay = true;
		for(int i=0; i<prohibitedNormalAngles.length; i++) {
			if((zDirectionNormalAngle > prohibitedNormalAngles[i]-tolerance) && (zDirectionNormalAngle < prohibitedNormalAngles[i]+tolerance)) {
				isOkay = false;
			}
		}
	is180RotationOkay = isOkay;
	}
	/**
	 * The bins need to be very specific for this morph.
	 * There should be exactly 3 bins
	 * Bin 0: Sharp Curvature
	 * Bin 1: Medium Curvature
	 * Bin 2: Straight Curvature
	 *
	 * Medium and straight are much closer to each other compared to sharp
	 *
	 * Medium and Straight are morphed into Sharp
	 * 	1. medium/straight should be rotated into sharps that are facing too much towards or away from viewer (looks straight)
	 *
	 * Sharp are either ROTATED ONLY or morphed into STRAIGHT (medium can be too close sometimes)
	 * 	1.Rotations should not cause direction of curvature to be facing towards or away from the viewer too much
	 *
	 */
	private void assignBins() {
		double radView = 5;
		//Copy scaledCurvatureBins from curvatureBins and scale each bin's bounds
		scaledCurvatureBins = new ArrayList<>();
		for(Bin<Double> bin:curvatureBins) {
//			Bin<Double> scaledBin = new Bin<Double>(bin.min*arcLen, bin.max*arcLen);
			Bin<Double> scaledBin = new Bin<Double>(bin.min*1, bin.max*1);
			scaledCurvatureBins.add(scaledBin);
		}

		//curvatureFlag = true;

		int closestCurvatureBin = findClosestCurvatureBin(scaledCurvatureBins, oldCurvature);

		//If straight already or medium
		if(closestCurvatureBin==1 || closestCurvatureBin==2) {
			rotationFlag = true;
			curvatureFlag = true;

			assignedCurvatureBin = 0;

		}
		//If curved already
		else {
			//if the curvature is bad (faces viewer or away too much) then we should rotate.
			if(!is180RotationOkay) {
				rotationFlag = true; //this rotation will end up being a 90 deg rotation
				curvatureFlag = false;
			}
			else { //curvature is good
				//if curvature is good, then we only rotate a percentage of the time
				boolean isRNGSuccess = stickMath_lib.rand01()<CHANCE_TO_CHANGE_ROTATION_NOT_CURVATURE;
				if(isRNGSuccess) {
					rotationFlag = true;
					curvatureFlag = false;

				}
				//Change Curvature ONLY
				else {
					rotationFlag = false;
					curvatureFlag = true;
					assignedCurvatureBin = 2;
				}
			}
		}
	}





	/**
	 * Differs in findClosestBin from Qualitative morph in that the value must be inside bin 0 to be assigned to it.
	 * @param binList
	 * @param value
	 * @return
	 */
	protected int findClosestCurvatureBin(List<Bin<Double>> binList, Double value) {
		int closestBin;
		//Find distance of our value to all mins of bins
		List<Double> minDistanceList = new ArrayList<>();
		for(int i=0; i<binList.size(); i++) {
			Double distance = Math.abs(value - binList.get(i).min);
			minDistanceList.add(i, distance);
		}
		int closestMinDistanceNdx = minDistanceList.indexOf(Collections.min(minDistanceList));
		//Find distance of our value to all maxes of bins
		List<Double> maxDistanceList = new ArrayList<>();
		for(int i=0; i<binList.size(); i++) {
			Double distance = Math.abs(value - binList.get(i).max);
			maxDistanceList.add(i, distance);
		}
		int closestMaxDistanceNdx = maxDistanceList.indexOf(Collections.min(maxDistanceList));

		//If inside a bin
		if(closestMinDistanceNdx == closestMaxDistanceNdx) {
			closestBin = closestMinDistanceNdx;
		}
		else{

			//Closer to Left than Right
			if(minDistanceList.get(closestMinDistanceNdx) < maxDistanceList.get(closestMaxDistanceNdx)) {
				closestBin = closestMinDistanceNdx;
			}
			else {
				closestBin = closestMaxDistanceNdx;
			}

			//MODIFICATION FOR CURVATURE
			if(closestBin==0) {
				closestBin = 1;
			}
		}
		return closestBin;

	}

	public boolean isCurvatureFlag() {
		return curvatureFlag;
	}

	public boolean isRotationFlag() {
		return rotationFlag;
	}

	public double getNewCurvature() {
		return newCurvature;
	}

	public double getNewRotation() {
		return newRotation;
	}

	public void setOldCurvature(double oldCurvature) {
		this.oldCurvature = oldCurvature;
	}

	public void setOldRotation(double oldRotation) {
		this.oldRotation = oldRotation;
	}
}