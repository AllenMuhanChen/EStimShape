package org.xper.allen.drawing.composition;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

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

	public void genMetricSimilarArc( MAxisArc inArc,int alignedPt,  double volatileRate) {
		boolean showDebug = false;
		if ( showDebug) 
			System.out.println("In MAxisArc.genSimilarArc()");
		double RadView = 5.0;
		//double[] orientationAngleRange = { Math.PI/12.0 , Math.PI/6.0}; // 15 ~ 30 degree
		// Nov 20th, the orientation change seems to be too large
		// since this is used to generate similar tube, we should make it more narrow
		double[] orientationAngleRange = { Math.PI/24.0 , Math.PI/12.0}; // 7.5 ~ 15 degree
		boolean[] chgFlg = new boolean[5];
		int i;
		//possible parameters , 1. mAxisCurvature, 2.ArcLen 3. orientation 4. devAngle
		// 0. decide what parameters to chg
		while (true) {
			for (i=1; i<=4; i++) {
				chgFlg[i] = false;
				if ( stickMath_lib.rand01() < volatileRate)
					chgFlg[i] = false; //TODO: CHANGE BACK TO TRUE
			}
			int a = 3;
			if ( a == 3) break;
			//debug
			if (inArc.rad <= 0.6 * RadView) {
				if ( chgFlg[1] != false || chgFlg[2] != false || chgFlg[3] != false || chgFlg[4] != false) 
					break;
			}
			else { // the in Arc is str8 line, then we don't want only devAngle chg, (which is not prominent) {
				if ( chgFlg[1] !=false || chgFlg[2] !=false || chgFlg[3] !=false) 
					break;
			}
		}

		if (showDebug) {
			System.out.println("the modification of mAxis are:");
			for (i=1; i<=4; i++) System.out.print(" "+ chgFlg[i]);
			System.out.println("");
		}


		double newRad = inArc.rad;
		double newArcLen = inArc.arcLen;
		Vector3d newTangent = new Vector3d(inArc.mTangent[ inArc.transRotHis_rotCenter]);
		double newDevAngle = inArc.transRotHis_devAngle;	

		// 1. mAxisCurvature	  
		if ( chgFlg[1] == true) {

			/*
			double totalRange;
			double oriRad = inArc.rad;
			if ( oriRad <= 0.6 * RadView )  { // origianlly small Rad arc
				double[] prob = {0.5, 1.0};
				int choice = stickMath_lib.pickFromProbDist( prob);
				if ( choice == 1) {
					while (true) {
						newRad = (stickMath_lib.rand01() * 0.4 + 0.2) * RadView;
						totalRange = 0.4 * RadView;
						if ( Math.abs( newRad - oriRad) > 0.2 * totalRange )
							break;
					}
				}
				else // chg to medium curvature regime
					newRad = (stickMath_lib.rand01() * 5.4 + 0.6) * RadView;
			}
			else if ( oriRad <= 6.0 * RadView) { // originall in medium regime
	 			double[] prob = {0.25, 0.75, 1.0};
				int choice = stickMath_lib.pickFromProbDist( prob);
				if (choice == 1)
					newRad = (stickMath_lib.rand01() * 0.4 + 0.2) * RadView;
				else if ( choice == 2) {
					while (true) {
						newRad = (stickMath_lib.rand01() * 5.4 + 0.6) * RadView;
						totalRange = 5.4 * RadView;
						if ( Math.abs(newRad - oriRad) > 0.2 * totalRange)
							break;
					}
				}
				else if ( choice == 3)
					newRad = 100000.0;
			}
			else {// str8 original curvature
				//always chg to medium curvature
				newRad = (stickMath_lib.rand01() * 5.4 + 0.6) * RadView; 
			}
			 */
		} // mAxisCurvature if

		// 2. ArcLen
		if ( chgFlg[2] == true) {
			double oriArcLen = inArc.arcLen;
			double length_lb = 2.0;		
			double length_ub = Math.min( Math.PI * newRad, RadView);
			double l_range = length_ub - length_lb;
			while (true) { //pick value btw length_lb, length_ub, but not very near or very far from original value
				newArcLen = stickMath_lib.randDouble( length_lb, length_ub);
				if ( oriArcLen > length_ub || oriArcLen < length_lb) // no need to nearby check
					break;
				if ( Math.abs( newArcLen - oriArcLen) >= 0.2 * l_range && 
						Math.abs( newArcLen - oriArcLen) <= 0.4 * l_range )
					break;
			}
		}

		// 3. orientation
		if ( chgFlg[3] == true) {
			Vector3d oriTangent = new Vector3d( inArc.mTangent[inArc.transRotHis_rotCenter]);
			while (true) {
				newTangent = stickMath_lib.randomUnitVec();
				double angle = newTangent.angle(oriTangent);
				if ( angle >= orientationAngleRange[0] && angle <= orientationAngleRange[1]) // 15 ~ 30 degree
					break;
			}
		}
		// 4. devAngle
		if ( chgFlg[4] == true)
		{
			System.out.println("AC1938243: devAngle changed");
			double oriDevAngle = inArc.transRotHis_devAngle;
			double diff = stickMath_lib.randDouble( Math.PI/6.0, Math.PI/3.0); // this diff is btw  30 - 60 degree
			if ( stickMath_lib.rand01() < 0.5)
				newDevAngle = oriDevAngle - diff;
			else
				newDevAngle = oriDevAngle + diff;
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
