package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.List;

import org.xper.allen.drawing.composition.AllenMAxisArc;

public class SizeQualitativeMorph extends QualitativeMorph{
	private boolean lengthFlag;
	private boolean thicknessFlag;

	private double oldLength;
	private double oldThickness;

	private double newLength;
	private double newThickness;
	private double normalizedOldLength;
	private double normalizedOldThickness;
	
	private double lengthMax;
	private double thicknessMax;
	
	// These bins should be defined to be NORMALIZED (0-1)
	public List<Bin<Double>> lengthBins;
	public List<Bin<Double>> thicknessBins;

	private int assignedLengthBin;
	private int assignedThicknessBin;

	private double radView;


	
	public SizeQualitativeMorph(double radView) {
		this.radView = radView;
		lengthBins = new ArrayList<Bin<Double>>();
		thicknessBins = new ArrayList<Bin<Double>>();
	}
	/**
	 * This needs to be run first
	 * @param oldLength
	 * @param oldThickness
	 */
	public void loadParams(double oldLength, double oldThickness) {
		setOldLength(oldLength);
		setOldThickness(oldThickness);
	}
	
	/**
	 * Run sometime after loadParams
	 * @param inArc
	 */
	public void calculate(AllenMAxisArc inArc) {
		assignBins(inArc);
		double minThickness = thicknessMax * (3/10);
		if(lengthFlag) {
			//unnormalize random value
			newLength = lengthMax * newValueFromBins(lengthBins, assignedLengthBin);
		}else {
			newLength = oldLength;
		}
		//assignedThicknessBin = 1; //DEBUG!
		if(thicknessFlag) {
			//unnormalize random value
			newThickness = thicknessMax * newValueFromBins(thicknessBins, assignedThicknessBin);
			if(newThickness < minThickness) {
				newThickness = minThickness;
			}
		} else {
			newThickness = oldThickness;
		}
	}

	/**
	 * The bins in this morph are normalized value (0-1, with 1 being the max possible length/thickness.
	 * It is done this way because the max thickness/length depends on variables of the arc
	 * So we normalize length and thickness to 0-1 before we assign bins,
	 * and after we've assigned bins and generated new values we unnormalize. 
	 * 
	 * @param inArc
	 */
	private void assignBins(AllenMAxisArc inArc) {
//		lengthMax = Math.min(Math.PI*inArc.getRad(), radView/1.5);
		lengthMax = radView/1.5;
//		thicknessMax = Math.min(inArc.getArcLen()/3, inArc.getRad()/1.5);
		thicknessMax = radView/9;
		normalizedOldLength = oldLength / lengthMax;
		normalizedOldThickness = oldThickness / thicknessMax;
		
		//TODO: Add difficulty here
		int closestLengthBin = findClosestBin(lengthBins, normalizedOldLength);
		int closestThicknessBin = findClosestBin(thicknessBins, normalizedOldThickness);
		
		lengthFlag = true;
		thicknessFlag = false;
		
		assignedLengthBin = chooseFurtherBin(lengthBins, closestLengthBin);
		assignedThicknessBin = chooseDifferentBin(thicknessBins, closestThicknessBin);
	}

	public double getNewLength() {
		return newLength;
	}

	public double getNewThickness() {
		return newThickness;
	}

	public void setOldLength(double oldLength) {
		this.oldLength = oldLength;
	}

	public void setOldThickness(double oldThickness) {
		this.oldThickness = oldThickness;
	}

	public boolean isLengthFlag() {
		return lengthFlag;
	}

	public boolean isThicknessFlag() {
		return thicknessFlag;
	}

	public double getRadView() {
		return radView;
	}

	public void setRadView(double radView) {
		this.radView = radView;
	}

	public double getOldLength() {
		return oldLength;
	}

	public double getOldThickness() {
		return oldThickness;
	}


}
