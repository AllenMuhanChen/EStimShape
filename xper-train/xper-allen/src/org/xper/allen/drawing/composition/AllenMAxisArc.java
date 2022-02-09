package org.xper.allen.drawing.composition;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.drawing.stick.MAxisArc;
import org.xper.drawing.stick.stickMath_lib;

/**
 * I created this class soley to be able to write a new genSiilarArc (genMetricSimilarArc) that
 * only changes length, orientation, and radius (of whole limb) slightly. 
 * 
 * This class should not generate any new fields and should be completely compatible with
 * its superclass. 
 * @author r2_allen
 *
 */
public class AllenMAxisArc extends MAxisArc {

	/**
	 * @param inArc
	 * @param alignedPt
	 * @param volatileRate
	 */
	public void genMetricSimilarArc( MAxisArc inArc,int alignedPt,  MetricMorphParams mmp) {
		boolean showDebug = false;
		//double[] orientationAngleRange = { Math.PI/12.0 , Math.PI/6.0}; // 15 ~ 30 degree
		// Nov 20th, the orientation change seems to be too large
		// since this is used to generate similar tube, we should make it more narrow
		//double[] orientationAngleRange = { Math.PI/24.0 , Math.PI/12.0}; // 7.5 ~ 15 degree
		
		int i;
		//possible parameters , 1. mAxisCurvature, 2.ArcLen 3. orientation 4. devAngle
		// 0. Initialize all possible parameters to previous values
		double newRad = inArc.rad;
		double newArcLen = inArc.arcLen;
		Vector3d newTangent = new Vector3d(inArc.mTangent[ inArc.transRotHis_rotCenter]);
		double newDevAngle = inArc.transRotHis_devAngle;	
	
		// 1. ArcLen
		/*
		 * AC: Modified random length assignment to limit it within a percentage bound of original arcLen 
		 */
		if(mmp.lengthFlag) {
			double oriArcLen = inArc.arcLen;
			mmp.lengthMagnitude.oldValue = oriArcLen;
			newArcLen = mmp.lengthMagnitude.calculateMagnitude();
		}
			
		// 2. orientation
		if(mmp.orientationFlag) {
			Vector3d oriTangent = new Vector3d( inArc.mTangent[inArc.transRotHis_rotCenter]);
			mmp.orientationMagnitude.oldVector = oriTangent;
			newTangent = mmp.orientationMagnitude.calculateVector();
		}
		
		//3. curvature
		if(mmp.curvatureFlag) {
			double oldRad = inArc.rad;
			mmp.curvatureMagnitude.oldValue = oldRad;
			newRad = mmp.curvatureMagnitude.calculateMagnitude(inArc.arcLen);
		}
		
		//4. rotation (along tangent axis)
		if(mmp.rotationFlag) {
			double oldDevAngle = inArc.transRotHis_devAngle;
			mmp.rotationMagnitude.oldValue = oldDevAngle;
			newDevAngle = mmp.rotationMagnitude.calculateMagnitude();	
		}
		
		// use the new required vlaue to generate and transROt the mAxisArc

		this.genArc(newRad, newArcLen); // the variable will be saved in this function

		Point3d finalPos = new Point3d( inArc.mPts[alignedPt]);
		// 
		this.transRotMAxis( alignedPt, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);
		//	Point3d finalPos = new Point3d(0.0,0.0,0.0);
		//	this.transRotMAxis( 26, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);

		if (showDebug)
		{
			System.out.println("rad    : " + inArc.rad + " -> " + newRad);
			System.out.println("arcLen : " + inArc.arcLen + " -> " + newArcLen);
			System.out.println("ori    : " + inArc.mTangent[inArc.transRotHis_rotCenter] + " -> " + newTangent);
			System.out.println("	angle btw is " + inArc.mTangent[inArc.transRotHis_rotCenter].angle(newTangent));
			System.out.println("devAng : " + inArc.transRotHis_devAngle + " -> " + newDevAngle);
			int rotCenter = inArc.transRotHis_rotCenter;
			System.out.println("ori rot center "+  rotCenter + " pos " + inArc.mPts[rotCenter] + "\ntan: "+ inArc.mTangent[rotCenter]);
			System.out.println("NEW rot center "+  rotCenter + " pos " + this.mPts[rotCenter] + "\ntan: "+ this.mTangent[rotCenter]);
			System.out.println("the input alignedPt is " + alignedPt);
			//			for (i=1; i<=51; i++)
			//			{
			//// 				double dist = mPts[i].distance( inArc.mPts[i]);
			//// 				if (dist > 0.01)
			//						System.out.println("MPts["+i+"]: " + this.mPts[i] + " " + inArc.mPts[i]);
			//				
			//			}
			//System.out.println("MPts[3]: " + this.mPts[3] + " " + inArc.mPts[3]);
			//System.out.println("MPts[20]: " + this.mPts[20] + " " + inArc.mPts[20]);

			System.out.println("");
		}

	}
}
