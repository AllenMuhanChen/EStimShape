package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

/**
 * Provides some useful methods using generics for Qualitative Morphs
 * @author r2_allen
 *
 */
public abstract class QualitativeMorph {

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
	
	public double[] vector2Angles(Vector3d vector) {
		double rho = 1;
		double beta = vector.z/rho;
		double alpha = Math.atan(vector.y/vector.x);
		double output[] = {alpha, beta};
		return output;
	}
	
	public static double[] Vector2Angles(Vector3d vector) {
		double rho = vector.length();
		double beta = vector.z/rho;
		double alpha = Math.atan(vector.y/vector.x);
		double output[] = {alpha, beta};
		return output;
	}
	/**
	 * Two spherical coordinate angles to cartesian vector
	 * @param alpha (or theta): angle on the X-Y plane between vector projection and X axis
	 * @param beta (or phi): angle on the Z plane between Z-axis and vector
	 * all angles should be in radians
	 * @return
	 */
	protected Vector3d angles2UnitVector(double alpha, double beta) {
		double rho = 1;
		double x = rho*Math.sin(beta)*Math.cos(alpha);
		double y = rho*Math.sin(beta)*Math.sin(alpha);
		double z = rho*Math.cos(beta);

		return new Vector3d(x,y,z);
	}

}
