package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import javax.vecmath.Vector2d;
import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class RadProfileQualitativeMorph extends QualitativeMorph{
	private boolean juncEnabled = false;
	private double binAngleDeviation = 5*Math.PI/180;

	private boolean juncFlag = false;
	private boolean midFlag = false;
	private boolean endFlag = false;

	private double oldJunc;
	private double oldMid;
	private double oldEnd;
	private Vector3d oldRadProfile;
	private double newJunc;
	private double newMid;
	private double newEnd;

	/*
	 * These bins should contain normalized data
	 */
	public List<Bin<Double>> juncBins;
	public List<Bin<Double>> midBins;
	public List<Bin<Double>> endBins;

	public List<Vector3d> radProfileBins;

	private int assignedRadProfileBin;

	public  int minToChange;
	public int maxToChange;

	public RadProfileQualitativeMorph(int minToChange, int maxToChange, boolean juncEnabled) {
		radProfileBins = new ArrayList<Vector3d>();
		this.minToChange = minToChange;
		this.maxToChange = maxToChange;
		this.juncEnabled = juncEnabled;
	}

	public void loadParams(double oldJunc, double oldMid, double oldEnd) {
		setOldJunc(oldJunc);
		setOldMid(oldMid);
		setOldEnd(oldEnd);
		setOldRadProfile(new Vector3d(oldJunc, oldMid, oldEnd));
	}

	public void calculate() {
		assignBins();

		if(isJuncEnabled()) {
			Vector3d newRadProfile = newVectorFromBins(radProfileBins, assignedRadProfileBin);
			setNewJunc(newRadProfile.getX());
			setNewMid(newRadProfile.getY());
			setNewEnd(newRadProfile.getZ());
		}
		else {
			Vector3d newRadProfile = newVectorFromBins(radProfileBins, assignedRadProfileBin);
			setNewJunc(oldRadProfile.getX());
			setNewMid(newRadProfile.getY());
			setNewEnd(newRadProfile.getZ());
		}
	}

	private void assignBins() {
		//		int closestJuncBin = findClosestBin(juncBins, oldJunc);
		//		int closestMidBin = findClosestBin(midBins, oldMid);
		//		int closestEndBin = findClosestBin(endBins, oldEnd);
		int closestRadProfileBin = findClosestRadProfileBin(radProfileBins, oldRadProfile);
		//Decide how many to change

		int numToMorph = stickMath_lib.randInt(minToChange, maxToChange);
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

		//		assignedJuncBin = chooseDifferentBin(juncBins, closestJuncBin);
		//		assignedMidBin = chooseDifferentBin(midBins, closestMidBin);
		//		assignedEndBin = chooseDifferentBin(endBins, closestEndBin);
		assignedRadProfileBin = chooseFurtherRadProfileBin(radProfileBins, closestRadProfileBin);

	}

	/**
	 *
	 * 05/11/22 Update to use JuncEnabled logic.
	 * @param binList
	 * @param assignedBin
	 * @return
	 */
	private Vector3d newVectorFromBins(List<Vector3d> binList, int assignedBin){
		if (isJuncEnabled()) {
			Vector3d newRadProfile = new Vector3d();
			while(true) {
				newRadProfile = new Vector3d(stickMath_lib.rand01(),stickMath_lib.rand01(),stickMath_lib.rand01());
				double angle = newRadProfile.angle(binList.get(assignedRadProfileBin));

				if(angle<getBinAngleDeviation()) {
					break;
				}
			}
			return newRadProfile;
		}
		else {
			Vector2d newRadProfile = new Vector2d();
			Vector2d bin = new Vector2d(binList.get(assignedRadProfileBin).getY(), binList.get(assignedRadProfileBin).getZ());
			while(true) {
				newRadProfile = new Vector2d(stickMath_lib.rand01(),stickMath_lib.rand01());
				double angle = newRadProfile.angle(bin);
				if(angle<getBinAngleDeviation()) {
					break;
				}
			}

			return new Vector3d(0, newRadProfile.getX(), newRadProfile.getY());
		}
	}

	private int findClosestRadProfileBin(List<Vector3d> binList, Vector3d nowVec) {
		int closestBin=-1;

		double minAngle=100000;
		for (int i=0; i<binList.size(); i++) {
			double angle = nowVec.angle(binList.get(i));
			if(angle<minAngle) {
				minAngle = angle;
				closestBin = i;
			}
		}

		return closestBin;

	}

	/**
	 * Chooses the furthest bin within 10 random pulls from the binList.
	 * @param <T>
	 * @param binList
	 * @param closestBin
	 * @return
	 */
	private <T> int chooseFurtherRadProfileBin(List<Vector3d> binList, int closestBin) {
		int newBin;
		int nTries = 10;
		int n=0;
		int furthestBin=-1;
		double maxAngle=0;
		while(n<nTries) {
			newBin = stickMath_lib.randInt(0, binList.size()-1);
			if(!juncEnabled) {
				Vector3d bin = binList.get(newBin);
				Vector3d cBin = binList.get(closestBin);
				Vector2d newBin2d = new Vector2d(bin.y, bin.z);
				Vector2d closestBin2d = new Vector2d(cBin.y, cBin.z);
				if(closestBin2d.angle(newBin2d) > maxAngle) {
					maxAngle = closestBin2d.angle(newBin2d);
					furthestBin = newBin;
				}
			}
			else {
				Vector3d closestBinVec = binList.get(closestBin);
				Vector3d newBinVec = binList.get(newBin);
				if (closestBinVec.angle(newBinVec) > maxAngle) {
					maxAngle = closestBinVec.angle(newBinVec);
					furthestBin = newBin;
				}
			}
			n++;
		}
		return furthestBin;
	}

	private <T> int chooseDifferentRadProfileBin(List<Vector3d> binList, int closestBin) {
		int newBin;
		while(true) {
			newBin = stickMath_lib.randInt(0, binList.size()-1);
			if(newBin != closestBin) {
				if(!juncEnabled) {
					Vector3d bin = binList.get(newBin);
					Vector3d cBin = binList.get(closestBin);
					Vector2d newBin2d = new Vector2d(bin.y, bin.z);
					Vector2d closestBin2d = new Vector2d(cBin.y, cBin.z);
					if(!newBin2d.equals(closestBin2d)) {
						break;
					}
				} else {
					break;
				}
			}
		}
		return newBin;
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

	//	public int getAssignedJuncBin() {
	//		return assignedJuncBin;
	//	}
	//
	//	public void setAssignedJuncBin(int assignedJuncBin) {
	//		this.assignedJuncBin = assignedJuncBin;
	//	}
	//
	//	public int getAssignedMidBin() {
	//		return assignedMidBin;
	//	}
	//
	//	public void setAssignedMidBin(int assignedMidBin) {
	//		this.assignedMidBin = assignedMidBin;
	//	}
	//
	//	public int getAssignedEndBin() {
	//		return assignedEndBin;
	//	}
	//
	//	public void setAssignedEndBin(int assignedEndBin) {
	//		this.assignedEndBin = assignedEndBin;
	//	}

	public boolean isMorphJunc() {
		return isJuncEnabled();
	}

	public void setMorphJunc(boolean morphJunc) {
		this.setJuncEnabled(morphJunc);
	}

	public boolean isJuncEnabled() {
		return juncEnabled;
	}

	private void setJuncEnabled(boolean juncEnabled) {
		this.juncEnabled = juncEnabled;
	}

	private Vector3d getOldRadProfile() {
		return oldRadProfile;
	}

	private void setOldRadProfile(Vector3d oldRadProfile) {
		this.oldRadProfile = oldRadProfile;
	}

	/**
	 * binAngleDeviation: max angles in rad a newVector should be from
	 * from specified vector in the bin.
	 * @return
	 */
	private double getBinAngleDeviation() {
		return binAngleDeviation;
	}

	private void setBinAngleDeviation(double binAngleDeviation) {
		this.binAngleDeviation = binAngleDeviation;
	}

}