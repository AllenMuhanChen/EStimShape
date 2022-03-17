package org.xper.allen.drawing.composition.qualitativemorphs;

import java.util.ArrayList;
import java.util.List;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;
/**
 * TODO: Some logic to randomly determine whether position, orientation or both is changed?
 * Have this logic be based on some metric for severity 
 * @author r2_allen
 *
 */
public class ObjectCenteredPositionQualitativeMorph extends QualitativeMorph{
	private double PERCENT_CHANGE_POSITION = 0;

	private boolean positionFlag = false;
	private boolean orientationFlag = false;

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
	private int assignedPositionBin;

	private Double[] baseTangentAngleSlideBounds;
	private Double[] perpendicularAngleSlideBounds;
	
	public final boolean rotateRelToBase =false;

	public ObjectCenteredPositionQualitativeMorph() {
		positionBins = new ArrayList<>();
	}

	public void loadParams(int oldPosition, Vector3d oldTangent) {
		setOldPosition(oldPosition);
		setOldTangent(oldTangent);
	}

	private void assignPositionBin() {
		if(stickMath_lib.rand01()<PERCENT_CHANGE_POSITION) {
			//Position
			int currentPositionBin = findClosestBin(positionBins, oldPosition);
			assignedPositionBin = chooseDifferentBin(positionBins, currentPositionBin);
			//TODO: logic to assign this flag
			positionFlag = true;
		} else {
			positionFlag = false;
		}

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


	public void calculateNewTangent(Vector3d baseTangent) {
//		assignAngleBins(baseTangent);

		Vector3d newTangent;
		
		double[] oldAngles = vector2Angles(oldTangent);
		double oldBaseTangentAngle = oldAngles[0];
		double oldPerpendicularAngle = oldAngles[1];
		
		double newBaseTangentAngle; 
		{//calc new baseTangentAngle (alpha/theta: angle on X-Y plane)
			//IF rotateRelToBase==false
			//specifying up/down/left/right
			//0: right
			//90: up
			//180: left
			//270: down
			//IF rotateRelToBase==true
			//pretend the tangent base is sitting on x-axis.
			//then the same angles apply. 
			//But baseTangent will be rotated like crazy so the absolute position of these limbs
			//is impossible to predict, but we can guarantee 
//			newBaseTangentAngle = newValueFromBins(baseTangentAngleBins, assignedBaseTangentAngleBin);

			double slideAmount = stickMath_lib.randDouble(baseTangentAngleSlideBounds[0], baseTangentAngleSlideBounds[1]);
			if(stickMath_lib.rand01()<0.5) {
				slideAmount = slideAmount * -1;
			}

			double slidAngle = oldBaseTangentAngle + slideAmount;

			while(slidAngle>360*Math.PI/180) {
				slidAngle-=360*Math.PI/180;
			}
			while(slidAngle<0) {
				slidAngle+=360*Math.PI/180;
			}
			newBaseTangentAngle = slidAngle;
		}
		

		double newPerpendicularAngle; 
		{//calc new perpendicularAngle (beta/phi: angle on Z-whatever plane)
			//IF rotateRelToBase==false
			//specifying coming towards or away from viewer. Between 0 and 180!
			//0:Towards viewer/out
			//90: Flat/ in the plane
			//180: Away from viewer/in
			//270: Flat but INVERTS Left/Right. Only makes sense to specify this between 0 and 180. 
//			newPerpendicularAngle = newValueFromBins(perpendicularAngleBins, assignedPerpendicularAngleBin);
			//newPerpendicularAngle = 90*Math.PI/180; //DEBUG
			double slideAmount = stickMath_lib.randDouble(baseTangentAngleSlideBounds[0], baseTangentAngleSlideBounds[1]);
			if(stickMath_lib.rand01()<0.5) {
				slideAmount = slideAmount * -1;
			}

			double slidAngle = oldPerpendicularAngle + slideAmount;

			while(slidAngle>180*Math.PI/180) {
				slidAngle-=180*Math.PI/180;
			}
			while(slidAngle<0) {
				slidAngle+=180*Math.PI/180;
			}
			newPerpendicularAngle = slidAngle;
		}

		//Use new angles to calculate new tangent vector while pretending newBaseTangentAngle and newPerpendicularAngle are relative to X-Y axis and Z-Y axis respectively
		newTangent = angles2UnitVector(newBaseTangentAngle, newPerpendicularAngle);


		//We can specify rotateRelToBase to true if we want rotations to be relative to base tangent
		if(rotateRelToBase)
		{//Rotate such that the x-axis is now the tangent of the base mAxis, the z-axis is now the perpendicular vector to the base tangent
			//Before this newTangent assumes that newBaseTangentAngle and newPerpendicularAngle are relative to x and z axis.
			//After this, they will be relative to the actual baseTangent and perpendicular to the baseTangent.	
			Vector3d xAxis = new Vector3d(1,0,0);
			Vector3d axisOfRot = new Vector3d();
			axisOfRot.cross(baseTangent, xAxis);
			axisOfRot.negate(); //negate because we are rotating the baseTangent to the xAxis not the otherway around.
			//https://www.geogebra.org/m/jcnba3fg use this to visualize this cross product. And note that the .angle() method only gives between 0 and pi.
			axisOfRot.normalize();
			double angle = baseTangent.angle(xAxis);
			AxisAngle4d rotInfo = new AxisAngle4d(axisOfRot, angle);
			Transform3D transMat = new Transform3D();
			transMat.setRotation(rotInfo);
			transMat.transform(newTangent);
		}

		this.newTangent = newTangent;
	}

	/**
	 * Modified because the first and last bin are actually close
	 */
	protected <T> int chooseFurtherBin(List<Bin<T>> binList, int closestBin) {
		int newBin = -1;

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
		else if (binList.size()==4){
			newBin=-1;
			if (closestBin==0) {
				newBin = 3;
			}
			else if (closestBin==3) {
				newBin = 1;
			}
			else if (closestBin == 1) {
				newBin = 3;
			}
			else if (closestBin == 2) {
				newBin = 0;
			}
			
		}
		return newBin;
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

	public Double[] getBaseTangentAngleSlideBounds() {
		return baseTangentAngleSlideBounds;
	}

	public void setBaseTangentAngleSlideBounds(Double[] baseTangentAngleSlideBounds) {
		this.baseTangentAngleSlideBounds = baseTangentAngleSlideBounds;
	}

	public Double[] getPerpendicularAngleSlideBounds() {
		return perpendicularAngleSlideBounds;
	}

	public void setPerpendicularAngleSlideBounds(Double[] perpendicularAngleSlideBounds) {
		this.perpendicularAngleSlideBounds = perpendicularAngleSlideBounds;
	}

}


