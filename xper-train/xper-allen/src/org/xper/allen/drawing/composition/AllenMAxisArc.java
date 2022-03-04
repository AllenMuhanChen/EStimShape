package org.xper.allen.drawing.composition;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorph;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.drawing.stick.MAxisArc;

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

	public Vector3d normal;
	/**
	 * @param inArc
	 * @param alignedPt
	 * @param volatileRate
	 */
	public void genQualitativeMorphArc( MAxisArc inArc,int alignedPt,  QualitativeMorphParams qmp) {
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
		//
		//TODO: Implement all of these parameters

		// 1. ArcLen
		/*
		 * AC: Modified random length assignment to limit it within a percentage bound of original arcLen 
		 */
		/*
		if(qmp.lengthFlag) {
			double oriArcLen = inArc.arcLen;
			//qmp.lengthMagnitude.oldValue = oriArcLen;
			newArcLen = oriArcLen;
		}
		 */
		
		// 2. orientation
		if(qmp.objCenteredPosQualMorph.isOrientationFlag()) {
			//Vector3d oriTangent = new Vector3d( inArc.mTangent[inArc.transRotHis_rotCenter]);
			newTangent = qmp.objCenteredPosQualMorph.getNewTangent();
		}
		

		
		//3. curvature
		if(qmp.curvatureRotationFlag) {
			newRad = qmp.curvRotQualMorph.getNewCurvature();
		}
		 
		
		//4. rotation (along tangent axis)
		if(qmp.curvatureRotationFlag) {
			newDevAngle = qmp.curvRotQualMorph.getNewRotation();	
		}
		 
		// use the new required vlaue to generate and transROt the mAxisArc

		this.genArc(newRad, newArcLen); // the variable will be saved in this function
		
		
		Point3d finalPos;
		if(qmp.objCenteredPosQualMorph.isPositionFlag()) {
			finalPos = qmp.objCenteredPosQualMorph.getNewPositionCartesian();
		}
		else {
			finalPos = new Point3d(inArc.mPts[alignedPt]);
		}
		// 
		transRotMAxis(alignedPt, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);
		
		
		
		//AC DEBUG - Testing Rotation  metrics
		System.out.println("AC858913: " + normal.x + ", " + normal.y + ", " + normal.z);
		double[] normalAngles = QualitativeMorph.Vector2Angles(normal); //in spherical coords
		System.out.println("AC50193: " + normalAngles[0] * 180 / Math.PI);
		System.out.println("AC50194: " + normalAngles[1] * 180 / Math.PI);
		
		
//		if(false) { //Method 1
//		//FINDING THE NORMAL OF THE ROTATION (direction the curve is facing)
//		Vector3d normal = new Vector3d(0,0,1);
//		
//		
////		//Rotate tangent to y-axis
//		Vector3d yAxis = new Vector3d(0,1,0);
//		Vector3d xAxis = new Vector3d(1,0,0);
//		Vector3d tangent =  new Vector3d(this.mTangent[transRotHis_rotCenter]);
//		System.out.println("AC858913: " + tangent.x + ", " + tangent.y + ", " + tangent.z);
//		
//		//		Transform3D transMat = new Transform3D();
////		{
////		Vector3d rotAxis = new Vector3d();
////		rotAxis.cross(yAxis, tangent);
////		double rotAngle = tangent.angle(yAxis);
////		AxisAngle4d rotation = new AxisAngle4d(rotAxis, rotAngle);
////		transMat.setRotation(rotation);
////		transMat.transform(tangent);
////		}
////		//Create normal facing upwards from limb
////		normal.cross(tangent, xAxis);
////		normal.absolute(); //TODO: MAY NEED TO TINKER
//		
//		//FIRST we pretend that the tangent is on the y-axis and the normal is the z-axis. 
//		//Rotate normal to devAngle
//		//Problem: when the leaf is rotated, the direction of rotation is dependent on the direction of the tangent. 
//		// We need to correct for this. 
//		Transform3D devTransMat = new Transform3D();
//		{
//			Vector3d rotAxis = new Vector3d(yAxis);
//			double rotAngle = newDevAngle;
//			AxisAngle4d rotation = new AxisAngle4d(rotAxis, rotAngle);
//			devTransMat.setRotation(rotation);
//			devTransMat.transform(normal);
//		}
//		
//		//Rotate normal with opposite rotation needs to bring the tangent to the y-axis
//		Transform3D transMat = new Transform3D();
//		{
//		Vector3d rotAxis = new Vector3d();
//		rotAxis.cross(yAxis, tangent);
//		rotAxis.negate();
//		double rotAngle = tangent.angle(yAxis);
//		AxisAngle4d rotation = new AxisAngle4d(rotAxis, rotAngle);
//		transMat.setRotation(rotation);
//		transMat.transform(normal);
//		}
//		
//		
//		//Rotate relative to Xaxis	
//		System.out.println("AC858914: " + normal.x + ", " + normal.y + ", " + normal.z);
//		double[] normalAngles = QualitativeMorph.Vector2Angles(normal); //in spherical coords
//		System.out.println("AC50193: " + normalAngles[0] * 180 / Math.PI);
//		System.out.println("AC50194: " + normalAngles[1] * 180 / Math.PI);
//		//	Point3d finalPos = new Point3d(0.0,0.0,0.0);
//		//	this.transRotMAxis( 26, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);
//		}
//		if(false) {
//			//FIND NORMAL
//			Vector3d tangent =  new Vector3d(this.mTangent[transRotHis_rotCenter]);
//			Vector3d yAxis = new Vector3d(0,1,0);
//			Vector3d normal = new Vector3d();
//			normal.cross(tangent, yAxis);
//			if(normal.z < 0) {
//				normal.negate();
//			}
//		}
//		
		//AC DEBUG
		//Point3d oriPos = inArc.mPts[alignedPt];
		//Point3d testPos = this.mPts[alignedPt];
		//double actualDistance = oriPos.distance(finalPos);
		//double expectedDistance = newArcLen/51;
		//double testDistance = testPos.distance(finalPos);
		//System.out.println("AC210484: " + "expected distance is " + expectedDistance + "whereas actual distance is " + actualDistance);
		//System.out.println("AC210484: " + "the test distance is: " + testDistance);
		//
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
		
		
		Point3d finalPos;
		if(mmp.positionFlag) {
			finalPos = mmp.positionMagnitude.newPos;
		}
		else {
			finalPos = new Point3d( inArc.mPts[alignedPt]);
		}
		// 
		transRotMAxis(alignedPt, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);
		//	Point3d finalPos = new Point3d(0.0,0.0,0.0);
		//	this.transRotMAxis( 26, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);

		
		//AC DEBUG
		//Point3d oriPos = inArc.mPts[alignedPt];
		//Point3d testPos = this.mPts[alignedPt];
		//double actualDistance = oriPos.distance(finalPos);
		//double expectedDistance = newArcLen/51;
		//double testDistance = testPos.distance(finalPos);
		//System.out.println("AC210484: " + "expected distance is " + expectedDistance + "whereas actual distance is " + actualDistance);
		//System.out.println("AC210484: " + "the test distance is: " + testDistance);
		//
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
	
	 // An important routine that will rotate and translate the MAxis Pts and tangent to new location
		// More precisely,	
		// seperate rotation of tangent into two step, first always rotate the rotCenter tangent to [1 0 0 ], 
		// then rotate to the final tangent, the reason to do so is some tricky thing about deviateAngle

		//Summary: June 2008	
		// Do two step rotation, and then rotate along tangent direction ( by deviateAngle)
		// Finally do the translation
	     /**
		 translate and rotate the MAxis to wanted condition
		 
		 
		 MODIFICATION BY ALLEN CHEN: 
		 have devAngle specified in params be absolute
		 Meaning we specify the final rotation we want it to be
		 So we should subtract the current dev angle from our goal devAngle to rotate such that we are on the specified dev angle.
		 
		 @param alignedPt integer, assign which point on mAxisArc to go to finalPos
		 @param finalPos Point3d, the final pos to align
		 @param rotCenter integer, the point play as center when rotate
		 @param finalTangent Vector3d, the tangent direction where the rotCenter Pt will face
		 @param deviateAngle double btw 0 ~ 2PI , the angle to rotate along the tangent direction
	     */
	     public void transRotMAxis(int alignedPt, Point3d finalPos, int rotCenter, Vector3d finalTangent, double deviateAngle)
	     {

//	 	System.out.println("transRot mAxis procedure:");
//	 	System.out.println("final pos: "+finalPos + "final tangent: "+finalTangent);
		/// 1. rotate to [0 0 1]
	      System.out.println("AC855912: " + this.transRotHis_devAngle);
		  int i;
		  Point3d oriPt = new Point3d();
		  Vector3d nowvec = new Vector3d(0,0,0);
		  Transform3D transMat = new Transform3D(); 	  
		  Vector3d oriTangent = mTangent[rotCenter];
		  Vector3d interTangent = new Vector3d(0,0,1);
		  double Angle = oriTangent.angle(interTangent);
	 	  Vector3d RotAxis = new Vector3d(0,0,0);
		  RotAxis.cross(oriTangent, interTangent);
		  RotAxis.normalize();
//	    System.out.println(oriTangent + " " + interTangent);
//	    System.out.println(Angle);
//	    System.out.println(RotAxis);

		  boolean skipRotate = false;
		  //July 24 2009, should we remove Angle == Math.PI
	          if ( Angle == 0.0 || Angle == Math.PI) // no need to turn
		    //if (Angle == 0.0) // remove the Angle == Math.PI on July24 2009
		  {
	      	     skipRotate = true;
//	 		System.out.println("Skip first rotation");
//	 		System.out.println("ori Tangent: " + oriTangent);
//	 		System.out.println("inter tangent: " + interTangent);
//	 		System.out.println("rad of the arc is " + rad);
	          }
	//System.out.println( mPts[30] + "  " + mPts[32]);
	//System.out.println("tangent[1] is at : "+ mTangent[1]);
	          if (!skipRotate)
		  {
	      		oriPt.set(mPts[rotCenter]);
			AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
			transMat.setRotation(axisInfo);
	       		for (i = 1 ; i <= getMaxStep(); i++)
	                {
				// rotate annd translate every mPts
	             		nowvec.sub(mPts[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
				transMat.transform(nowvec); 
				mPts[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt
				
	             		// Original matlab code:    mPts[i] = (RotVecArAxe(nowvec', RotAxis', Angle))' + oriPt;             
	             		// rotate the Tangent vector along the maxis
				transMat.transform(mTangent[i]);             		
	       		}
		   }
	          
	          // 1.5 AC. Counter current deviate angle
			   if (  rad < 999999 ) // if the mAxisArc is a str8 line, no need to do this part
		  	   {
				   oriPt.set(mPts[rotCenter]);
				   
				   AxisAngle4d axisInfo = new AxisAngle4d( finalTangent, -transRotHis_devAngle);   		
				   transMat.setRotation(axisInfo);
		   		for (i = 1 ; i <= getMaxStep(); i++)
				{
					nowvec.sub(mPts[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
					transMat.transform(nowvec); 
					mPts[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt		
					         
					transMat.transform(mTangent[i]);             	             				
		   		}
			   }
			   
			   //1.6 AC Define our normal angle
			   normal = new Vector3d(0,1,0);
	          
	//System.out.println( mPts[30] + "  " + mPts[32]);   
	//System.out.println("tangent[1] is at : "+ mTangent[1]);   
	        /// 2. rotate to targetTangent

	  	   oriTangent.set( interTangent);   
	       Angle = oriTangent.angle(finalTangent);
	   	   RotAxis.cross(oriTangent, finalTangent);
		   RotAxis.normalize();

	   	   skipRotate = false;
	   	   // NOTE: 3/30/2010
	   	   // when angle = PI, we need to rotate, but rotAxis is arbitrary
	   	   // when angle == pi, means finalTangent = [ 0 0 -1]
	   	   // so rotate along [1 0 0 ] will be fine
	   	   //BUT, this is a key part of program
	   	   // if anything goes wrong, just come back to activate follow line
	   	   //if ( Angle == 0.0 || Angle == Math.PI) // THE KEY LINE TO CHANGE BACK
	   		if (Angle == 0.0) // remove the Angle == Math.PI on July24 2009
		   {
	      	        skipRotate = true;
	    		System.out.println("Skip second rotation");
	       }
	   		if (Angle == Math.PI)
	   		{
	   	        skipRotate = true;
	    		System.out.println("Skip second rotation, due to [0 0 -1], not ideal");
	   		}
	    
		   if (!skipRotate)
		   {
	      		oriPt.set(mPts[rotCenter]);
			AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
			transMat.setRotation(axisInfo);
	  
	      		for (i = 1 ; i <= getMaxStep(); i++)
	                {
				// rotate annd translate every mPts
	             		nowvec.sub(mPts[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
				transMat.transform(nowvec); 
				mPts[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt			
	             		// Original matlab code:    mPts[i] = (RotVecArAxe(nowvec', RotAxis', Angle))' + oriPt;             
	             		// rotate the Tangent vector along the maxis
				transMat.transform(mTangent[i]);             		
	       		}
	      		//AC ADDITION:
	      		transMat.transform(normal);
	           }
	//System.out.println("tangent[1] is at : "+ mTangent[1]);      
	//System.out.println("mPts[1] is at : "+ mPts[1]);
		/// 3. rotate along the tangent axis by deviate Angle
		  double nowDeviateAngle = transRotHis_devAngle;
		   if (  rad < 100000 ) // if the mAxisArc is a str8 line, no need to do this part
	  	   {
			   oriPt.set(mPts[rotCenter]);
			   nowDeviateAngle = deviateAngle - transRotHis_devAngle;
			   AxisAngle4d axisInfo = new AxisAngle4d( finalTangent, nowDeviateAngle);   		
			   transMat.setRotation(axisInfo);
	   		for (i = 1 ; i <= getMaxStep(); i++)
			{
				nowvec.sub(mPts[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
				transMat.transform(nowvec); 
				mPts[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt		
				         
				transMat.transform(mTangent[i]);             	             				
	   		}
	   		//AC ADDITION:
	   		transMat.transform(normal);
		   }
	   //System.out.println("tangent[1] is at : "+ mTangent[1]);
	//System.out.println("mPts[1] is at : "+ mPts[1]);
		/// 4. translation
		   oriPt.set( mPts[alignedPt]);
		   Vector3d transVec = new Vector3d(0,0,0);
		   transVec.sub(finalPos, oriPt);
		   for (i=1; i<=getMaxStep(); i++)
		   {
			mPts[i].add(transVec);
		   }
	        /// 5. save the transrot history into recording data
		   transRotHis_alignedPt = alignedPt;
		   transRotHis_rotCenter = rotCenter;
		   
		   // July 24 2009, this is the key point
		   // change from = to set in May , so we should not have the 
		   // wrongly finalTangent probblem in the future
		   //transRotHis_finalPos = finalPos;
		   transRotHis_finalPos.set(finalPos);
		   //transRotHis_finalTangent = finalTangent;
		   transRotHis_finalTangent.set( finalTangent);
		   transRotHis_devAngle = nowDeviateAngle;
	//System.out.println("tangent[1] is at : "+ mTangent[1]);
	     }
}
