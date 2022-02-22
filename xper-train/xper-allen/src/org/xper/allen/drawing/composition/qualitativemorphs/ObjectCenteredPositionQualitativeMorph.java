package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.List;

import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class ObjectCenteredPositionQualitativeMorph {
	public List<Bin<Integer>> positionBins = new ArrayList<>();
	/**
	 * angle relative to the tangent of the base limb's mAXis
	 * Will only be used for position morphs where the limb ends up on the end. 
	 */
	public List<Bin<Double>> baseTangentAngleBins = new ArrayList<>(); 
	public List<Bin<Double>> perpendicularAngleBins = new ArrayList<>(); //angle relative to the vector that is perpendicular to the base limb's Tangent line. 

	private int assignedPositionBin;
	private int assignedBaseTangentAngleBin;
	private int assignedPerpendicularAngleBin;

	private Vector3d baseTangent;
	
	public ObjectCenteredPositionQualitativeMorph() {
	}

	public void assignBins(int oldPosition, Vector3d oldTangent, Vector3d baseTangent) {
		this.baseTangent = baseTangent;
		//Position
		for(int i=0; i<positionBins.size(); i++) {
			if(oldPosition<=positionBins.get(i).max && oldPosition>=positionBins.get(i).min) {
				assignedPositionBin = i;
				//TODO: this is not the proper assignedBin
				
			}
		}
		//Angles
		//baseTangentAngle
		for(int i=0; i<baseTangentAngleBins.size(); i++) {
			double oldBaseTangentAngle = oldTangent.angle(baseTangent);
			if(oldBaseTangentAngle<=baseTangentAngleBins.get(i).max && oldBaseTangentAngle>=baseTangentAngleBins.get(i).min) {
				assignedBaseTangentAngleBin = i;
			}
		}
		//perpendicularAngle
		for(int i=0; i<perpendicularAngleBins.size(); i++) {
			Vector3d oldPerpendicularVector = new Vector3d();
			oldPerpendicularVector.cross(baseTangent, new Vector3d(0,1,0));
			double oldPerpendicularAngle = oldTangent.angle(oldPerpendicularVector);
			if(oldPerpendicularAngle<=perpendicularAngleBins.get(i).max && oldPerpendicularAngle>=perpendicularAngleBins.get(i).min) {
				assignedPerpendicularAngleBin = i;
			}
		}
	}

	/*
	public ObjectCenteredPositionQualitativeMorphMagnitude calculateNewValues() {
		int newPosition;
		Vector3d newTangent;
		
		
		
		
		
		ObjectCenteredPositionQualitativeMorphMagnitude mag = new ObjectCenteredPositionQualitativeMorphMagnitude();
		mag.position = newPosition;
		mag.tangent = newTangent;
		return mag;
	}
	*/

	public ObjectCenteredPositionQualitativeMorphMagnitude calculateNewValues() {
		ObjectCenteredPositionQualitativeMorphMagnitude mag = new ObjectCenteredPositionQualitativeMorphMagnitude();
		int newPosition;
		Vector3d newTangent;
		
		{//position
			int min = positionBins.get(assignedPositionBin).min;
			int max = positionBins.get(assignedPositionBin).max;
			if(min==max) {
				newPosition=min;
			}
			else {
				newPosition = stickMath_lib.randInt(min, max);
			}
		}
		
		double newBaseTangentAngle;
		{//calc new baseTangentAngle (alpha/theta: angle on X-Y plane)
			double min = baseTangentAngleBins.get(assignedBaseTangentAngleBin).min;
			double max = baseTangentAngleBins.get(assignedBaseTangentAngleBin).max;
			newBaseTangentAngle = stickMath_lib.randDouble(min, max);	
		}
		
		double newPerpendicularAngle;
		{//calc new perpendicularAngle (beta/phi: angle on Z-whatever plane)
			double min = perpendicularAngleBins.get(assignedPerpendicularAngleBin).min;
			double max = perpendicularAngleBins.get(assignedPerpendicularAngleBin).max;
			newPerpendicularAngle = stickMath_lib.randDouble(min,max);
		}
		
		//Use new angles to calculate new tangent vector while pretending newBaseTangentAngle and newPerpendicularAngle are relative to X-Y axis and Z-Y axis respectively
		newTangent = angles2UnitVector(newBaseTangentAngle, newPerpendicularAngle);
		
		{//Shift such that mAxis Tangent of base is on the x-axis
		Vector3d xAxis = new Vector3d(1,0,0);
		Vector3d yAxis = new Vector3d(0,1,0);
		Vector3d zAxis = new Vector3d(0,0,1);
		double shiftX = Math.acos(baseTangent.dot(xAxis)/ (baseTangent.length()*xAxis.length()));
		double shiftY = Math.acos(baseTangent.dot(yAxis)/ (baseTangent.length()*yAxis.length()));
		double shiftZ = Math.acos(baseTangent.dot(zAxis)/ (baseTangent.length()*zAxis.length()));
		stickMath_lib.rotateVectorAroundOrigin(newTangent, shiftX, shiftY, shiftZ);
		}
		
		mag.position = newPosition;
		mag.tangent = newTangent;
		return mag;
	}

	public class ObjectCenteredPositionQualitativeMorphMagnitude{
		public int position;
		public Vector3d tangent;
	}
	
	/**
	 * Two spherical coordinate angles to cartesian vector
	 * @param alpha (or theta): angle on the X-Y plane between vector projection and X axis
	 * @param beta (or phi): angle on the Z plane between Z-axis and vector
	 * all angles should be in radians
	 * @return
	 */
	private Vector3d angles2UnitVector(double alpha, double beta) {
		double rho = 1;
		double x = rho*Math.sin(beta)*Math.cos(alpha);
		double y = rho*Math.sin(beta)*Math.sin(alpha);
		double z = rho*Math.cos(beta);
		
		return new Vector3d(x,y,z);
	}

}


