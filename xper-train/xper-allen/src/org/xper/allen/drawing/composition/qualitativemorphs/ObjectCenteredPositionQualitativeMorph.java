package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.List;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

public class ObjectCenteredPositionQualitativeMorph {
	private boolean positionFlag;
	private boolean orientationFlag;

	private int oldPosition;
	private Vector3d oldTangent;

	private int newPosition;
	private Vector3d newTangent;
	private Point3d newPositionCartesian;
	
	public List<Bin<Integer>> positionBins;
	/**
	 * angle relative to the tangent of the base limb's mAXis
	 * Will only be used for position morphs where the limb ends up on the end. 
	 */
	public List<Bin<Double>> baseTangentAngleBins; 
	public List<Bin<Double>> perpendicularAngleBins; //angle relative to the vector that is perpendicular to the base limb's Tangent line. 

	private int assignedPositionBin;
	private int assignedBaseTangentAngleBin;
	private int assignedPerpendicularAngleBin;

	public ObjectCenteredPositionQualitativeMorph() {
		positionBins = new ArrayList<>();
		baseTangentAngleBins = new ArrayList<>();
		perpendicularAngleBins = new ArrayList<>();
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

	private void assignPositionBin() {
		//Position
		for(int i=0; i<positionBins.size(); i++) {
			if(oldPosition<=positionBins.get(i).max && oldPosition>=positionBins.get(i).min) {
				assignedPositionBin = i;
				//TODO: this is not the proper assignedBin

			}
		}
		//TODO: logic to assign this flag
		positionFlag = true;
		
	}
	
	public void calculateNewPosition() {
		assignPositionBin();
		
		int newPosition;
		int min = positionBins.get(assignedPositionBin).min;
		int max = positionBins.get(assignedPositionBin).max;
		if(min==max) {
			newPosition=min;
		}
		else {
			newPosition = stickMath_lib.randInt(min, max);
		}
		this.newPosition = newPosition;
	}
	
	private void assignAngleBins(Vector3d baseTangent, double devAngle) {
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
			Vector3d crossProductVector = new Vector3d(0,1,0);
			//stickMath_lib.rotateVectorAroundOrigin(devAngleVector, 0, 0, devAngle);
			oldPerpendicularVector.cross(baseTangent, crossProductVector);
			double oldPerpendicularAngle = oldTangent.angle(oldPerpendicularVector);
			if(oldPerpendicularAngle<=perpendicularAngleBins.get(i).max && oldPerpendicularAngle>=perpendicularAngleBins.get(i).min) {
				assignedPerpendicularAngleBin = i;
			}
		}
		orientationFlag = true;

	}
	
	public void calculateNewTangent(Vector3d baseTangent, double devAngle) {
		assignAngleBins(baseTangent, devAngle);
		
		Vector3d newTangent;

		double newBaseTangentAngle;
		{//calc new baseTangentAngle (alpha/theta: angle on X-Y plane)
			double min = baseTangentAngleBins.get(assignedBaseTangentAngleBin).min;
			double max = baseTangentAngleBins.get(assignedBaseTangentAngleBin).max;
			newBaseTangentAngle = stickMath_lib.randDouble(min, max);
			newBaseTangentAngle = 180*Math.PI/180;
		}

		double newPerpendicularAngle;
		{//calc new perpendicularAngle (beta/phi: angle on Z-whatever plane)
			double min = perpendicularAngleBins.get(assignedPerpendicularAngleBin).min;
			double max = perpendicularAngleBins.get(assignedPerpendicularAngleBin).max;
			newPerpendicularAngle = stickMath_lib.randDouble(min,max);
			newPerpendicularAngle = 90*Math.PI/180;
		}

		//Use new angles to calculate new tangent vector while pretending newBaseTangentAngle and newPerpendicularAngle are relative to X-Y axis and Z-Y axis respectively
		newTangent = angles2UnitVector(newBaseTangentAngle, newPerpendicularAngle);
		//newTangent = new Vector3d(1,0,0);
		
		{//Rotate such that the x-axis is now the tangent of the base mAxis, the z-axis is now the perpendicular vector to the base tangent
			//Before this newTangent assumes that newBaseTangentAngle and newPerpendicularAngle are relative to x and z axis.
			//After this, they will be relative to the actual baseTangent and perpendicular to the baseTangent.	
			Vector3d xAxis = new Vector3d(1,0,0);

			Vector3d axisOfRot = new Vector3d();
			axisOfRot.cross(baseTangent, xAxis);
			axisOfRot.absolute();
			double angle = baseTangent.angle(xAxis);
			AxisAngle4d rotInfo = new AxisAngle4d(axisOfRot, angle);
			Transform3D transMat = new Transform3D();
			transMat.setRotation(rotInfo);
			transMat.transform(newTangent);
//			double shiftX = rad2deg*Math.acos(baseTangent.dot(xAxis)/ (baseTangent.length()*xAxis.length()));
//			double shiftY = rad2deg*Math.acos(baseTangent.dot(yAxis)/ (baseTangent.length()*yAxis.length()));
//			double shiftZ = rad2deg*Math.acos(baseTangent.dot(zAxis)/ (baseTangent.length()*zAxis.length()));
//			stickMath_lib.rotateVectorAroundOrigin(newTangent, shiftX, shiftY, shiftZ);
//			stickMath_lib.rotateVectorAroundOrigin(baseTangent, shiftX, shiftY, shiftZ);
		}

		this.newTangent = newTangent;
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

	public boolean isPositionFlag() {
		return positionFlag;
	}

	public boolean isOrientationFlag() {
		return orientationFlag;
	}

	public void setOldPosition(int oldPosition) {
		this.oldPosition = oldPosition;
	}

	public void setOldTangent(Vector3d oldTangent) {
		this.oldTangent = oldTangent;
	}

	public int getNewPosition() {
		return newPosition;
	}

	public Vector3d getNewTangent() {
		return newTangent;
	}






	public Point3d getNewPositionCartesian() {
		return newPositionCartesian;
	}






	public void setNewPositionCartesian(Point3d newPositionCartesian) {
		this.newPositionCartesian = newPositionCartesian;
	}

}


