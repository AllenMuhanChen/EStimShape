package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import org.xper.drawing.stick.stickMath_lib;

public class RadProfileQualitativeMorph extends QualitativeMorph{
	private boolean juncEnabled = false;
	
	private boolean juncFlag;
	private boolean midFlag;
	private boolean endFlag;
	
	private double oldJunc;
	private double oldMid;
	private double oldEnd;
	
	private double newJunc;
	private double newMid;
	private double newEnd;
	
	/*
	 * These bins should contain normalized data
	 */
	public List<Bin<Double>> juncBins;
	public List<Bin<Double>> midBins;
	public List<Bin<Double>> endBins;
	
	private int assignedJuncBin;
	private int assignedMidBin;
	private int assignedEndBin;
	
	public RadProfileQualitativeMorph() {
		juncBins = new ArrayList<Bin<Double>>();
		midBins = new ArrayList<Bin<Double>>();
		endBins = new ArrayList<Bin<Double>>();
	}
	
	public void loadParams(double oldJunc, double oldMid, double oldEnd) {
		setOldJunc(oldJunc);
		setOldMid(oldMid);
		setOldEnd(oldEnd);
	}
	
	public void calculate() {
		assignBins();
		
		if(juncFlag) {
			newJunc = newValueFromBins(juncBins, assignedJuncBin);
		}
		if(midFlag) {
			newMid = newValueFromBins(midBins, assignedMidBin);
		}
		if(endFlag) {
			newEnd = newValueFromBins(endBins, assignedEndBin);
		}
	}

	private void assignBins() {
		int closestJuncBin = findClosestBin(juncBins, oldJunc);
		int closestMidBin = findClosestBin(midBins, oldMid);
		int closestEndBin = findClosestBin(endBins, oldEnd);
		//Decide how many to change
		int numToMorph = stickMath_lib.randInt(1, 2);
		//Decide which to change
		List<Integer> locList = new LinkedList<>(); //1-junc, 2-mid, 3-end
		if(isJuncEnabled()) {
			locList.add(1);
		}
		locList.add(2); 
		locList.add(3);
		Collections.shuffle(locList);
		
		List<Integer> toMorphList = new LinkedList<>();
		for(int i=0; i<numToMorph; i++) {
			toMorphList.add(locList.get(i));
		}
		
		for(int loc : locList) {
			if (loc==1)
				juncFlag = true;
			if (loc==2)
				midFlag = true;
			if (loc==3)
				endFlag = true;
		}
		
		assignedJuncBin = chooseDifferentBin(juncBins, closestJuncBin);
		assignedMidBin = chooseDifferentBin(midBins, closestMidBin);
		assignedEndBin = chooseDifferentBin(endBins, closestEndBin);
	}
	
	public boolean isJuncFlag() {
		return juncFlag;
	}

	public void setJuncFlag(boolean juncFlag) {
		this.juncFlag = juncFlag;
	}

	public boolean isMidFlag() {
		return midFlag;
	}

	public void setMidFlag(boolean midFlag) {
		this.midFlag = midFlag;
	}

	public boolean isEndFlag() {
		return endFlag;
	}

	public void setEndFlag(boolean endFlag) {
		this.endFlag = endFlag;
	}

	public double getOldJunc() {
		return oldJunc;
	}

	public void setOldJunc(double oldJunc) {
		this.oldJunc = oldJunc;
	}

	public double getOldMid() {
		return oldMid;
	}

	public void setOldMid(double oldMid) {
		this.oldMid = oldMid;
	}

	public double getOldEnd() {
		return oldEnd;
	}

	public void setOldEnd(double oldEnd) {
		this.oldEnd = oldEnd;
	}

	public double getNewJunc() {
		return newJunc;
	}

	public void setNewJunc(double newJunc) {
		this.newJunc = newJunc;
	}

	public double getNewMid() {
		return newMid;
	}

	public void setNewMid(double newMid) {
		this.newMid = newMid;
	}

	public double getNewEnd() {
		return newEnd;
	}

	public void setNewEnd(double newEnd) {
		this.newEnd = newEnd;
	}

	public List<Bin<Double>> getJuncBins() {
		return juncBins;
	}

	public void setJuncBins(List<Bin<Double>> juncBins) {
		this.juncBins = juncBins;
	}

	public List<Bin<Double>> getMidBins() {
		return midBins;
	}

	public void setMidBins(List<Bin<Double>> midBins) {
		this.midBins = midBins;
	}

	public List<Bin<Double>> getEndBins() {
		return endBins;
	}

	public void setEndBins(List<Bin<Double>> endBins) {
		this.endBins = endBins;
	}

	public int getAssignedJuncBin() {
		return assignedJuncBin;
	}

	public void setAssignedJuncBin(int assignedJuncBin) {
		this.assignedJuncBin = assignedJuncBin;
	}

	public int getAssignedMidBin() {
		return assignedMidBin;
	}

	public void setAssignedMidBin(int assignedMidBin) {
		this.assignedMidBin = assignedMidBin;
	}

	public int getAssignedEndBin() {
		return assignedEndBin;
	}

	public void setAssignedEndBin(int assignedEndBin) {
		this.assignedEndBin = assignedEndBin;
	}

	public boolean isMorphJunc() {
		return isJuncEnabled();
	}

	public void setMorphJunc(boolean morphJunc) {
		this.setJuncEnabled(morphJunc);
	}

	private boolean isJuncEnabled() {
		return juncEnabled;
	}

	private void setJuncEnabled(boolean juncEnabled) {
		this.juncEnabled = juncEnabled;
	}
	
}
