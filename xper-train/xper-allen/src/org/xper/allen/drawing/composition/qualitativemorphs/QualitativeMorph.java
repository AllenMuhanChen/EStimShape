package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

/**
 * Provides some useful methods using generics for Qualitative Morphs
 * 
 * Some basic architecture for QualitativeMorph subclass objects:
 * 	1. QualitativeMorph objects are created once and used for the rest of the execution of stimuli generation
 * 	2. The job of these objects are to store parameters and use them later to generate new parameters based on 
 * 		both constant (bins) and constantly changing (current Arc params) parameters.
 * 	3. Obviously stored params need to be data members
 * 	4. However rapidly changing params should be passed in as function arguments for safety
 * 		against not resetting them and readability. 
 * @author r2_allen
 *
 */
public abstract class QualitativeMorph {
	
	//public abstract void loadParams();
	
	protected double newValueFromBins(List<Bin<Double>> binList, int assignedBin){
		double min = binList.get(assignedBin).min;
		double max = binList.get(assignedBin).max;

		return stickMath_lib.randDouble(min, max);
	}

	protected int findClosestBin(List<Bin<Integer>> binList, Integer value) {
		int closestBin;
		//Find distance of our value to all mins of bins 
		List<Integer> minDistanceList = new ArrayList<>();
		for(int i=0; i<binList.size(); i++) {
			Integer distance = Math.abs(value - binList.get(i).min); 
			minDistanceList.add(i, distance);
		}
		int closestMinDistanceNdx = minDistanceList.indexOf(Collections.min(minDistanceList));
		//Find distance of our value to all maxes of bins
		List<Integer> maxDistanceList = new ArrayList<>();
		for(int i=0; i<binList.size(); i++) {
			Integer distance = Math.abs(value - binList.get(i).max); 
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
		}
		return closestBin;

	}

	protected int findClosestBin(List<Bin<Double>> binList, Double value) {
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
		}
		return closestBin;

	}

	protected <T> int chooseDifferentBin(List<Bin<T>> binList, int closestBin) {
		int newBin;
		while(true) {
			newBin = stickMath_lib.randInt(0, binList.size()-1);
			if(newBin != closestBin) {
				break;
			}
		}
		return newBin;
	}

	/**
	 * Cant choose the closest bin or a neighboring bin. 
	 * @param <T>
	 * @param binList
	 * @param closestBin
	 * @return
	 */
	protected <T> int chooseFurtherBin(List<Bin<T>> binList, int closestBin) {
		int newBin;

		if(binList.size()==2) {
			return chooseDifferentBin(binList, closestBin);
		}
		else if (binList.size()==3) {
			if(closestBin==1) { //middle bin, is adjacent to all bins. 
				return chooseDifferentBin(binList, closestBin);
			}
			else {
				while(true) {
					newBin = stickMath_lib.randInt(0, binList.size()-1);
					if(Math.abs(newBin - closestBin) > 1){
						break;
					}
				}
			}
		}
		else {
			while(true) {
				newBin = stickMath_lib.randInt(0, binList.size()-1);
				if(Math.abs(newBin - closestBin) > 1){
					break;
				}
			}
		}

		return newBin;
	}

	public double[] vector2Angles(Vector3d vector) {
		double rho = vector.length();
		double beta = Math.acos(vector.z/rho);
		double alpha = Math.atan(vector.y/vector.x);
		double output[] = {alpha, beta};
		return output;
	}

	public static double[] Vector2Angles(Vector3d vector) {
		double rho = vector.length();
		double beta = Math.acos(vector.z/rho);
		double alpha = Math.atan(vector.y/vector.x);
		double output[] = {alpha, beta};
		return output;
	}
	/**
	 * Two spherical coordinate angles to cartesian vector
	 * @param alpha (or theta): angle on the X-Y plane between vector projection and X axis
	 * @param beta (or phi): angle between Z-axis and vector
	 * all angles should be in radians
	 * @return
	 */
	public static Vector3d angles2UnitVector(double alpha, double beta) {
		double rho = 1.0;
		double x = rho*Math.sin(beta)*Math.cos(alpha);
		double y = rho*Math.sin(beta)*Math.sin(alpha);
		double z = rho*Math.cos(beta);

		return new Vector3d(x,y,z);
	}
	
	public static Vector3d angles2Vector(double alpha, double beta, double length) {
		double rho = length;
		double x = rho*Math.sin(beta)*Math.cos(alpha);
		double y = rho*Math.sin(beta)*Math.sin(alpha);
		double z = rho*Math.cos(beta);

		return new Vector3d(x,y,z);
	}



}
