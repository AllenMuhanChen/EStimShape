package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class CurvatureRotationQualitativeMorph extends QualitativeMorph{
	private boolean curvatureFlag;
	private boolean rotationFlag;

	private double oldCurvature;
	private double oldRotation;

	private double newCurvature;
	private double newRotation;

	public List<Bin<Double>> curvatureBins;
	public List<Bin<Double>> rotationBins;

	private int assignedCurvatureBin;
	private int assignedRotationBin;

	public double CHANCE_TO_CHANGE_ROTATION_NOT_CURVATURE = 1;
	
	public CurvatureRotationQualitativeMorph() {
		curvatureBins = new ArrayList<Bin<Double>>();
		rotationBins = new ArrayList<Bin<Double>>();
	}

	public void calculate() {
		assignBins();

		
		if(curvatureFlag) {
			double min = curvatureBins.get(assignedCurvatureBin).min;
			double max = curvatureBins.get(assignedCurvatureBin).max;

			newCurvature = stickMath_lib.randDouble(min, max);
		}
		else {
			newCurvature = oldCurvature;
		}

		if(rotationFlag) {
			if(oldRotation > 180*(Math.PI/180))
				newRotation = oldRotation - 180*(Math.PI/180);
			else 
				newRotation = oldRotation + 180*(Math.PI/180);
		}
		else {
			newRotation = oldRotation;
		}

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
	 * Sharp are either ROTATED ONLY or morphed into Medium/Straight
	 * 
	 */
	private void assignBins() {

		curvatureFlag = true;

		int closestCurvatureBin = findClosestCurvatureBin(curvatureBins, oldCurvature);

		//If straight already
		if(closestCurvatureBin==1 || closestCurvatureBin==2) {
			rotationFlag = false;
			curvatureFlag = true;
			
			assignedCurvatureBin = 0;

		}
		//If curved already
		else {
			//Change Rotation ONLY
			boolean isRNGSuccess = stickMath_lib.rand01()<CHANCE_TO_CHANGE_ROTATION_NOT_CURVATURE;
			if(isRNGSuccess) {
				rotationFlag = true;
				curvatureFlag = false;
//				assignedRotationBin = chooseDifferentBin(rotationBins, closestRotationBin);
			}
			//Change Curvature ONLY
			else {
				rotationFlag = false;
				curvatureFlag = true;
				assignedCurvatureBin = stickMath_lib.randInt(1, 2);
			}
		}
		System.out.println("AC 908247: " + closestCurvatureBin + " assigned to " + assignedCurvatureBin);
		

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
			System.out.println("AC 908245: INSIDE OF BIN");
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
				System.out.println("AC 908246: ASSIGNED TO MID");
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
