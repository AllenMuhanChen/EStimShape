package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

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
}
