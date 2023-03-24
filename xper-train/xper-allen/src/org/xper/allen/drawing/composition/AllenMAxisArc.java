package org.xper.allen.drawing.composition;

import java.util.Random;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;
import org.xper.alden.drawing.drawables.Drawable;
import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorph;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
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
	public Vector3d normal = new Vector3d();
	private int MaxStep = 51;

	private double rad;
	private double curvature;
	private double arcLen;
	public double angleExtend;

	private int branchPt;
	private Point3d[] mPts= new Point3d[MaxStep+1];
	private Vector3d[] mTangent= new Vector3d[MaxStep+1];
	private double[] localArcLen = new double[MaxStep+1];

	private int transRotHis_alignedPt;
	private int transRotHis_rotCenter;
	private Point3d transRotHis_finalPos = new Point3d();
	private Vector3d transRotHis_finalTangent = new Vector3d();
	private double transRotHis_devAngle;

	public AllenMAxisArc() {
		//setRad(100.0); //nothing, just debug
		int i;
		for (i=0; i<=MaxStep; i++) {
			getmPts()[i] = new Point3d();
			getmTangent()[i] = new Vector3d();
		}
	}

	/**
	 * Constructor for generating an upsampled MAXis arc.
	 * @param maxStep
	 */
	public AllenMAxisArc(int maxStep) {
		super();
		setMaxStep(maxStep);
		setmPts(new Point3d[getMaxStep()+1]);
		setmTangent(new Vector3d[getMaxStep()+1]);
		setLocalArcLen(new double[getMaxStep()+1]);
		int i;
		for (i=0; i<=getMaxStep(); i++) {
			getmPts()[i] = new Point3d();
			getmTangent()[i] = new Vector3d();
		}
	}

	public void copyParamsForUpSample(AllenMAxisArc in) {
		int i;
		setRad(in.getRad());
		setCurvature(in.getCurvature());
		setArcLen(in.getArcLen());
		setAngleExtend(in.getAngleExtend());
		//		setBranchPt(in.getBranchPt());

		double maxStepCorrection = (double) getMaxStep()/ (double) in.MaxStep;
		if(in.getTransRotHis_alignedPt()==1) {
			setTransRotHis_alignedPt(in.getTransRotHis_alignedPt());
		} else if(in.getTransRotHis_alignedPt()==in.getMaxStep()) {
			setTransRotHis_alignedPt(getMaxStep());
		}
		else {
			setTransRotHis_alignedPt((int) Math.round(in.getTransRotHis_alignedPt() * maxStepCorrection));
		}

		if(in.getTransRotHis_rotCenter()==1) {
			setTransRotHis_rotCenter(in.getTransRotHis_rotCenter());
		} else if(in.getTransRotHis_rotCenter()==in.getMaxStep()) {
			setTransRotHis_rotCenter(getMaxStep());
		}
		else {
			setTransRotHis_rotCenter((int) Math.round(in.getTransRotHis_rotCenter()* maxStepCorrection));
		}
		getTransRotHis_finalPos().set( in.getTransRotHis_finalPos());
		//		setTransRotHis_finalPos(new Point3d(in.getmPts()[in.getTransRotHis_alignedPt()]));
		getTransRotHis_finalTangent().set( in.getTransRotHis_finalTangent());
		setTransRotHis_devAngle(in.getTransRotHis_devAngle());
		setNormal(in.getNormal());

//		System.out.println("AC00000: " + getTransRotHis_rotCenter());
	}

	public void copyFrom(AllenMAxisArc in) {
		int i;
		setRad(in.getRad());
		setCurvature(in.getCurvature());
		setArcLen(in.getArcLen());
		setAngleExtend(in.getAngleExtend());
		setBranchPt(in.getBranchPt());
		for (i=1; i<= getMaxStep(); i++) {
			getmPts()[i].set( in.getmPts()[i]);
			getmTangent()[i].set( in.getmTangent()[i]);
			getLocalArcLen()[i] = in.getLocalArcLen()[i];
		}

		setTransRotHis_alignedPt(in.getTransRotHis_alignedPt());
		setTransRotHis_rotCenter(in.getTransRotHis_rotCenter());
		getTransRotHis_finalPos().set( in.getTransRotHis_finalPos());
		getTransRotHis_finalTangent().set( in.getTransRotHis_finalTangent());
		setTransRotHis_devAngle(in.getTransRotHis_devAngle());
		setNormal(new Vector3d(in.getNormal()));
	}



	/**
	 * @param inArc
	 * @param alignedPt
	 */
	public void genQualitativeMorphArc( AllenMAxisArc inArc,int alignedPt,  QualitativeMorphParams qmp) {
		boolean showDebug = false;
		//double[] orientationAngleRange = { Math.PI/12.0 , Math.PI/6.0}; // 15 ~ 30 degree
		// Nov 20th, the orientation change seems to be too large
		// since this is used to generate similar tube, we should make it more narrow
		//double[] orientationAngleRange = { Math.PI/24.0 , Math.PI/12.0}; // 7.5 ~ 15 degree

		int i;
		//possible parameters , 1. mAxisCurvature, 2.ArcLen 3. orientation 4. devAngle
		// 0. Initialize all possible parameters to previous values
		double newRad = inArc.getRad();
		double newArcLen = inArc.getArcLen();
		Vector3d newTangent = new Vector3d(inArc.getmTangent()[ inArc.getTransRotHis_rotCenter()]);
		double newDevAngle = inArc.getTransRotHis_devAngle();
		//
		//TODO: Implement all of these parameters

		// 1. ArcLen
		if(qmp.sizeQualMorph.isLengthFlag()) {
			newArcLen = qmp.sizeQualMorph.getNewLength();
		}


		// 2. orientation
		if(qmp.objCenteredPosQualMorph.isOrientationFlag()) {
			//Vector3d oriTangent = new Vector3d( inArc.mTangent[inArc.transRotHis_rotCenter]);
			newTangent = qmp.objCenteredPosQualMorph.getNewTangent();
		}



		//3. curvature
		if(qmp.curvRotQualMorph.isCurvatureFlag()) {
			newRad = qmp.curvRotQualMorph.getNewCurvature();
		}


		//4. rotation (along tangent axis)
		if(qmp.curvRotQualMorph.isRotationFlag()) {
			newDevAngle = qmp.curvRotQualMorph.getNewRotation();
		}

		// use the new required vlaue to generate and transROt the mAxisArc

		genArc(newRad, newArcLen); // the variable will be saved in this function


		Point3d finalPos;
		if(qmp.objCenteredPosQualMorph.isPositionFlag()) {
			finalPos = qmp.objCenteredPosQualMorph.getNewPositionCartesian();
		}
		else {
			finalPos = new Point3d(inArc.getmPts()[alignedPt]);
		}
		//
//		transRotMAxis(alignedPt, finalPos, inArc.getTransRotHis_rotCenter(), newTangent, newDevAngle);
		transRotMAxis(alignedPt, finalPos, alignedPt, newTangent, newDevAngle);


		//		//AC DEBUG - Testing Rotation  metrics
		//		System.out.println("AC858913: " + normal.x + ", " + normal.y + ", " + normal.z);
		//		double[] normalAngles = QualitativeMorph.Vector2Angles(normal); //in spherical coords
		//		System.out.println("AC50193: " + normalAngles[0] * 180 / Math.PI);
		//		System.out.println("AC50194: " + normalAngles[1] * 180 / Math.PI);
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


			System.out.println("rad    : " + inArc.getRad() + " -> " + newRad);
			System.out.println("arcLen : " + inArc.getArcLen() + " -> " + newArcLen);
			System.out.println("ori    : " + inArc.getmTangent()[inArc.getTransRotHis_rotCenter()] + " -> " + newTangent);
			System.out.println("	angle btw is " + inArc.getmTangent()[inArc.getTransRotHis_rotCenter()].angle(newTangent));
			System.out.println("devAng : " + inArc.getTransRotHis_devAngle() + " -> " + newDevAngle);
			int rotCenter = inArc.getTransRotHis_rotCenter();
			System.out.println("ori rot center "+  rotCenter + " pos " + inArc.getmPts()[rotCenter] + "\ntan: "+ inArc.getmTangent()[rotCenter]);
			System.out.println("NEW rot center "+  rotCenter + " pos " + this.getmPts()[rotCenter] + "\ntan: "+ this.getmTangent()[rotCenter]);
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
	 */
	public void genMetricSimilarArc( AllenMAxisArc inArc,int alignedPt,  MetricMorphParams mmp) {
		boolean showDebug = false;
		//double[] orientationAngleRange = { Math.PI/12.0 , Math.PI/6.0}; // 15 ~ 30 degree
		// Nov 20th, the orientation change seems to be too large
		// since this is used to generate similar tube, we should make it more narrow
		//double[] orientationAngleRange = { Math.PI/24.0 , Math.PI/12.0}; // 7.5 ~ 15 degree

		int i;
		//possible parameters , 1. mAxisCurvature, 2.ArcLen 3. orientation 4. devAngle
		// 0. Initialize all possible parameters to previous values
		double newRad = inArc.getRad();
		double newArcLen = inArc.getArcLen();
		Vector3d newTangent = new Vector3d(inArc.getmTangent()[ inArc.getTransRotHis_rotCenter()]);
		double newDevAngle = inArc.getTransRotHis_devAngle();

		// 1. ArcLen
		/*
		 * AC: Modified random length assignment to limit it within a percentage bound of original arcLen
		 */
		if(mmp.lengthFlag) {
			double oriArcLen = inArc.getArcLen();
			mmp.lengthMagnitude.oldValue = oriArcLen;
			newArcLen = mmp.lengthMagnitude.calculateMagnitude();
		}

		// 2. orientation
		if(mmp.orientationFlag) {
			//			inArc.getmTangent()[inArc.get]
			Vector3d oriTangent = new Vector3d( inArc.getmTangent()[inArc.getTransRotHis_rotCenter()]);
			mmp.orientationMagnitude.setOldVector(oriTangent);
			newTangent = mmp.orientationMagnitude.calculateVector();
		}

		//3. curvature
		if(mmp.curvatureFlag) {
			double oldRad = inArc.getRad();
			mmp.curvatureMagnitude.setOldValue(oldRad);
			newRad = mmp.curvatureMagnitude.calculateMagnitude(inArc);
		}

		//4. rotation (along tangent axis)
		if(mmp.rotationFlag) {
			double oldDevAngle = inArc.getTransRotHis_devAngle();
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
			finalPos = new Point3d( inArc.getmPts()[alignedPt]);
		}
		//
		transRotMAxis(alignedPt, finalPos, inArc.getTransRotHis_rotCenter(), newTangent, newDevAngle);
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


			System.out.println("rad    : " + inArc.getRad() + " -> " + newRad);
			System.out.println("arcLen : " + inArc.getArcLen() + " -> " + newArcLen);
			System.out.println("ori    : " + inArc.getmTangent()[inArc.getTransRotHis_rotCenter()] + " -> " + newTangent);
			System.out.println("	angle btw is " + inArc.getmTangent()[inArc.getTransRotHis_rotCenter()].angle(newTangent));
			System.out.println("devAng : " + inArc.getTransRotHis_devAngle() + " -> " + newDevAngle);
			int rotCenter = inArc.getTransRotHis_rotCenter();
			System.out.println("ori rot center "+  rotCenter + " pos " + inArc.getmPts()[rotCenter] + "\ntan: "+ inArc.getmTangent()[rotCenter]);
			System.out.println("NEW rot center "+  rotCenter + " pos " + this.getmPts()[rotCenter] + "\ntan: "+ this.getmTangent()[rotCenter]);
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

		 @param alignedPt integer, assign which point on mAxisArc to go to finalPos
		 @param finalPos Point3d, the final pos to align
		 @param rotCenter integer, the point play as center when rotate
		 @param finalTangent Vector3d, the tangent direction where the rotCenter Pt will face
		 @param deviateAngle double btw 0 ~ 2PI , the angle to rotate along the tangent direction
	 */
	@Override
	public void transRotMAxis(int alignedPt, Point3d finalPos, int rotCenter, Vector3d finalTangent, double deviateAngle)
	{

		//	 	System.out.println("AllenMAXis transRot mAxis procedure:");
		//	 	System.out.println("final pos: "+finalPos + "final tangent: "+finalTangent);

		int i;
		Point3d oriPt = new Point3d();
		Vector3d nowvec = new Vector3d(0,0,0);
		Transform3D transMat = new Transform3D();
		Vector3d oriTangent = getmTangent()[rotCenter];

		/// 1. rotate to [0 0 1]
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
//			if (Angle == 0.0) // remove the Angle == Math.PI on July24 2009
		{
			skipRotate = true;
				 		System.out.println("Skip first rotation");
			//	 		System.out.println("ori Tangent: " + oriTangent);
			//	 		System.out.println("inter tangent: " + interTangent);
			//	 		System.out.println("rad of the arc is " + rad);
		}
		//System.out.println( mPts[30] + "  " + mPts[32]);
		//System.out.println("tangent[1] is at : "+ mTangent[1]);
		if (!skipRotate)
		{
			oriPt.set(getmPts()[rotCenter]);
			AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
			transMat.setRotation(axisInfo);
			for (i = 1 ; i <= getMaxStep(); i++)
			{
				// rotate annd translate every mPts
				nowvec.sub(getmPts()[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
				transMat.transform(nowvec);
				getmPts()[i].add(nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt

				// Original matlab code:    mPts[i] = (RotVecArAxe(nowvec', RotAxis', Angle))' + oriPt;
				// rotate the Tangent vector along the maxis
				transMat.transform(getmTangent()[i]);
			}
		}

		//1.6 AC Define our normal angle
//		normal = new Vector3d(0,1,0);

		//System.out.println( mPts[30] + "  " + mPts[32]);
		//System.out.println("tangent[1] is at : "+ mTangent[1]);
		/// 2. rotate to targetTangent


		//CALCULATE NORMAL
		normal = new Vector3d(0, 1, 0);
		Vector3d rotAxis = new Vector3d();
		double x = Math.cos(deviateAngle);
		double y = Math.sin(deviateAngle);
		Vector3d finalNormal = new Vector3d(x,y,0);

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
			oriPt.set(getmPts()[rotCenter]);
			AxisAngle4d axisInfo = new AxisAngle4d(RotAxis, Angle);
			transMat.setRotation(axisInfo);

			for (i = 1 ; i <= getMaxStep(); i++)
			{
				// rotate annd translate every mPts
				nowvec.sub(getmPts()[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
				transMat.transform(nowvec);
				getmPts()[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt
				// Original matlab code:    mPts[i] = (RotVecArAxe(nowvec', RotAxis', Angle))' + oriPt;
				// rotate the Tangent vector along the maxis
				transMat.transform(getmTangent()[i]);
			}
			//AC ADDITION:
			transMat.transform(normal);
			transMat.transform(finalNormal);
		}
		//System.out.println("tangent[1] is at : "+ mTangent[1]);
		//System.out.println("mPts[1] is at : "+ mPts[1]);
		/// 3. rotate along the tangent axis by deviate Angle
		double nowDeviateAngle = deviateAngle;
//		if ( getRad() < 100000 ) // if the mAxisArc is a str8 line, no need to do this part
		if(true)
		{
//			System.err.println("Before Angle Rotate to Original: " + getmTangent()[alignedPt].toString());
//			//ROTATE OPPOSITE OF CURRENT DEV ANGLE TO RETURN TO ZERO
//			oriPt.set(getmPts()[rotCenter]);
//
//			nowDeviateAngle = getTransRotHis_devAngle();
//			AxisAngle4d axisInfo = new AxisAngle4d(finalTangent, -nowDeviateAngle);
//
//			transMat.setRotation(axisInfo);
//			System.err.println("Angle Rotate to Original: " + axisInfo.getAngle());
//			for (i = 1 ; i <= getMaxStep(); i++)
//			{
//				nowvec.sub(getmPts()[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
//				transMat.transform(nowvec);
//				getmPts()[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt
//
//				transMat.transform(getmTangent()[i]);
//			}
//			System.err.println("After Angle Rotate to Original: " + getmTangent()[alignedPt].toString());



			//ROTATE TO DESIRED DEV ANGLE
			oriPt.set(getmPts()[rotCenter]);
			rotAxis.cross(normal, finalNormal);
			rotAxis.normalize();
			AxisAngle4d axisInfo = new AxisAngle4d(rotAxis, normal.angle(finalNormal));

//			transMat.setRotation(axisInfo);
//			nowDeviateAngle = deviateAngle;
//			axisInfo = new AxisAngle4d(finalTangent, nowDeviateAngle);
			transMat.setRotation(axisInfo);
			for (i = 1 ; i <= getMaxStep(); i++)
			{
				nowvec.sub(getmPts()[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
				transMat.transform(nowvec);
				getmPts()[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt

				transMat.transform(getmTangent()[i]);
			}
			//AC ADDITION:
//			transMat.transform(this.normal);
			this.normal = finalNormal;
		} else {
			nowDeviateAngle = getTransRotHis_devAngle();
		}
		//System.out.println("tangent[1] is at : "+ mTangent[1]);
		//System.out.println("mPts[1] is at : "+ mPts[1]);
		/// 4. translation
		oriPt.set( getmPts()[alignedPt]);
		Vector3d transVec = new Vector3d(0,0,0);
		transVec.sub(finalPos, oriPt);
		for (i=1; i<=getMaxStep(); i++)
		{
			getmPts()[i].add(transVec);
		}
		/// 5. save the transrot history into recording data
		setTransRotHis_alignedPt(alignedPt);
		setTransRotHis_rotCenter(rotCenter);

		// July 24 2009, this is the key point
		// change from = to set in May , so we should not have the
		// wrongly finalTangent probblem in the future
		//transRotHis_finalPos = finalPos;
		//		getTransRotHis_finalPos().set(finalPos);
//		setTransRotHis_finalPos(finalPos);
		//transRotHis_finalTangent = finalTangent;
		getTransRotHis_finalPos().set(finalPos);
		getTransRotHis_finalTangent().set(finalTangent);
		setTransRotHis_devAngle(nowDeviateAngle);
		//System.out.println("tangent[1] is at : "+ mTangent[1]);
	}


	public Point3d[] constructUpSampledMpts(int numSamples) {


		AllenMAxisArc upSampledArc = new AllenMAxisArc(numSamples);
		upSampledArc.copyParamsForUpSample(this);
		upSampledArc.genArc();

		int alignedPt = upSampledArc.getTransRotHis_alignedPt();
		Point3d finalPos = new Point3d(upSampledArc.getTransRotHis_finalPos());
		int rotCenter = upSampledArc.getTransRotHis_rotCenter();
		Vector3d finalTangent = new Vector3d(upSampledArc.getTransRotHis_finalTangent());
		double devAngle = upSampledArc.getTransRotHis_devAngle();


//		int alignedPt = upSampledArc.getTransRotHis_rotCenter();
//		Point3d finalPos = new Point3d(getmPts()[getTransRotHis_alignedPt()]);
//		int rotCenter = alignedPt;
//		Vector3d finalTangent = new Vector3d(getmTangent()[getTransRotHis_rotCenter()]);
//		double devAngle = getTransRotHis_devAngle();
//		System.out.println("AC DEV ANGLE!!~!!!!!: " + getTransRotHis_devAngle());
//		System.out.println("AC SAMPLE DEV ANGLE@@@@@: " + upSampledArc.getTransRotHis_devAngle());
//		System.out.println("AC ALIGNED PT: " + getTransRotHis_alignedPt());
//		System.out.println("AC UP-SAMPLE ALIGNED PT: " + alignedPt);
//		System.out.println("AC ORIGINAL FINALPOS: " + getTransRotHis_finalPos());
//		System.out.println("AC UP-SAMPLE FINALPOS: " + finalPos);
//
//		System.out.println("AC ROT CENTER: " + getTransRotHis_rotCenter());
//		System.out.println("AC UP-SAMPLE ROT CENTER: " + rotCenter);
//		System.out.println("AC ORIGINAL TANGENT: " + getTransRotHis_finalTangent());
//		System.out.println("AC UP-SAMPLE TANGENT: " + finalTangent);

		upSampledArc.transRotMAxis(alignedPt, finalPos, rotCenter, finalTangent, devAngle);

//		System.out.println("AC AFTER-ROTATE FINALPOS: " + upSampledArc.getTransRotHis_finalPos());
//		System.out.println("AC AFTER-ROTATE TANGENT: " + upSampledArc.getTransRotHis_finalTangent());
		return upSampledArc.getmPts();
	}

	/**
	 * Gen an Arc with the object's current parameters. Rad and ArcLen should already
	 * be specified.
	 */
	public void genArc() {
		int step;
		double nowu, now_angle;
		setAngleExtend(getArcLen() / getRad());

		if ( getRad() >= 99999) //str8 line condition
		{
			for (step=1; step <=getMaxStep(); step++)
			{
				nowu = ((double)step-1) / ((double)getMaxStep()-1);

				getmPts()[step]= new Point3d(0,0, nowu* getArcLen());
				getmTangent()[step]= new Vector3d(0,0,1);
				getLocalArcLen()[step] = getArcLen();
				//				System.out.println(upSampledMpts[step]);
			}
		}
		else
		{
			for (step = 1 ; step <=getMaxStep(); step++)
			{
				nowu = ((double)step-1) / ((double)getMaxStep()-1);
				now_angle = nowu * getAngleExtend() - 0.5 * getAngleExtend();
				//	 System.out.println("step " + step+ " now u " + nowu + " angle " + now_angle);
				//	 System.out.println(rad*Math.cos(now_angle));
				//	 System.out.println(rad*Math.sin(now_angle));
				//	 System.out.println(mAxis_pts.length);
				getmPts()[step] = new Point3d(0, getRad() * Math.cos(now_angle), getRad()* Math.sin(now_angle));
				getmTangent()[step] = new Vector3d(0, -getAngleExtend()*getRad()*Math.sin(now_angle), getAngleExtend()*getRad()*Math.cos(now_angle));
				//System.out.println(mAxis_tangent[step]);
				getLocalArcLen()[step] = getmTangent()[step].length();
				getmTangent()[step].normalize();
				//System.out.println(mAxis_tangent[step] + "  len:  " + mAxis_arcLen[step]);
				//				System.out.println(upSampledMpts[step]);
			}

		}
//		setmPts(upSampledMpts);
//		setLocalArcLen(upSampledLocalArcLen);
//		setmTangent(upSampledMTangent);


	}

	public void genSimilarArc(AllenMAxisArc inArc,int alignedPt,  double volatileRate) {
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
					chgFlg[i] = true;
			}
			int a = 3;
			if ( a == 3) break;
			//debug
			if (inArc.getRad() <= 0.6 * RadView) {
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


		double newRad = inArc.getRad();
		double newArcLen = inArc.getArcLen();
		Vector3d newTangent = new Vector3d(inArc.getmTangent()[ inArc.getTransRotHis_rotCenter()]);
		double newDevAngle = inArc.getTransRotHis_devAngle();

		// 1. mAxisCurvature
		if ( chgFlg[1] == true) {
			double totalRange;
			double oriRad = inArc.getRad();
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
		} // mAxisCurvature if

		// 2. ArcLen
		if ( chgFlg[2] == true) {
			double oriArcLen = inArc.getArcLen();
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
			Vector3d oriTangent = new Vector3d( inArc.getmTangent()[inArc.getTransRotHis_rotCenter()]);
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
			double oriDevAngle = inArc.getTransRotHis_devAngle();
			double diff = stickMath_lib.randDouble( Math.PI/6.0, Math.PI/3.0); // this diff is btw  30 - 60 degree
			if ( stickMath_lib.rand01() < 0.5)
				newDevAngle = oriDevAngle - diff;
			else
				newDevAngle = oriDevAngle + diff;
		}


		// use the new required vlaue to generate and transROt the mAxisArc

		this.genArc(newRad, newArcLen); // the variable will be saved in this function

		Point3d finalPos = new Point3d( inArc.getmPts()[alignedPt]);
		//
		this.transRotMAxis( alignedPt, finalPos, inArc.getTransRotHis_rotCenter(), newTangent, newDevAngle);
// 	Point3d finalPos = new Point3d(0.0,0.0,0.0);
// 	this.transRotMAxis( 26, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);

		if (showDebug)
		{
			System.out.println("rad    : " + inArc.getRad() + " -> " + newRad);
			System.out.println("arcLen : " + inArc.getArcLen() + " -> " + newArcLen);
			System.out.println("ori    : " + inArc.getmTangent()[inArc.getTransRotHis_rotCenter()] + " -> " + newTangent);
			System.out.println("	angle btw is " + inArc.getmTangent()[inArc.getTransRotHis_rotCenter()].angle(newTangent));
			System.out.println("devAng : " + inArc.getTransRotHis_devAngle() + " -> " + newDevAngle);
			int rotCenter = inArc.getTransRotHis_rotCenter();
			System.out.println("ori rot center "+  rotCenter + " pos " + inArc.getmPts()[rotCenter] + "\ntan: "+ inArc.getmTangent()[rotCenter]);
			System.out.println("NEW rot center "+  rotCenter + " pos " + this.getmPts()[rotCenter] + "\ntan: "+ this.getmTangent()[rotCenter]);
			System.out.println("the input alignedPt is " + alignedPt);
// 			for (i=1; i<=51; i++)
// 			{
// // 				double dist = mPts[i].distance( inArc.mPts[i]);
// // 				if (dist > 0.01)
// 						System.out.println("MPts["+i+"]: " + this.mPts[i] + " " + inArc.mPts[i]);
//
// 			}
			//System.out.println("MPts[3]: " + this.mPts[3] + " " + inArc.mPts[3]);
			//System.out.println("MPts[20]: " + this.mPts[20] + " " + inArc.mPts[20]);

			System.out.println("");
		}

	}

	public void drawNormal(float red, float green, float blue)
	{
		//use the oGL draw line function to draw out the mAxisArc
		int i;
		GL11.glColor3f(red, green, blue);
		GL11.glBegin(GL11.GL_LINE_STRIP);

		for (i=1; i<= getNormal().length(); i++)
		{
			//GL11.glVertex3d(mPts[i].getX(), mPts[i].getY(), mPts[i].getZ());
			GL11.glVertex3d(getNormal().x, getNormal().y, getNormal().z);
		}

		GL11.glEnd();

	}


	public Vector3d getNormal() {
		return normal;
	}

	public int getMaxStep() {
		return MaxStep;
	}

	public double getRad() {
		return rad;
	}

	public double getCurvature() {
		return curvature;
	}

	public double getArcLen() {
		return arcLen;
	}

	public double getAngleExtend() {
		return angleExtend;
	}

	public int getBranchPt() {
		return branchPt;
	}

	public Point3d[] getmPts() {
		return mPts;
	}

	public Vector3d[] getmTangent() {
		return mTangent;
	}

	public double[] getLocalArcLen() {
		return localArcLen;
	}

	public int getTransRotHis_alignedPt() {
		return transRotHis_alignedPt;
	}

	public int getTransRotHis_rotCenter() {
		return transRotHis_rotCenter;
	}

	public Point3d getTransRotHis_finalPos() {
		return transRotHis_finalPos;
	}

	public Vector3d getTransRotHis_finalTangent() {
		return transRotHis_finalTangent;
	}

	public double getTransRotHis_devAngle() {
		return transRotHis_devAngle;
	}

	public void setNormal(Vector3d normal) {
		this.normal = normal;
	}

	public void setRad(double rad) {
		this.rad = rad;
	}

	public void setCurvature(double curvature) {
		this.curvature = curvature;
	}

	public void setArcLen(double arcLen) {
		this.arcLen = arcLen;
	}

	public void setAngleExtend(double angleExtend) {
		this.angleExtend = angleExtend;
	}

	public void setBranchPt(int branchPt) {
		this.branchPt = branchPt;
	}

	public void setmPts(Point3d[] mPts) {
		this.mPts = mPts;
	}

	public void setmTangent(Vector3d[] mTangent) {
		this.mTangent = mTangent;
	}

	public void setLocalArcLen(double[] localArcLen) {
		this.localArcLen = localArcLen;
	}

	public void setTransRotHis_alignedPt(int transRotHis_alignedPt) {
		this.transRotHis_alignedPt = transRotHis_alignedPt;
	}

	public void setTransRotHis_rotCenter(int transRotHis_rotCenter) {
		this.transRotHis_rotCenter = transRotHis_rotCenter;
	}

	public void setTransRotHis_finalPos(Point3d transRotHis_finalPos) {
		this.transRotHis_finalPos = transRotHis_finalPos;
	}

	public void setTransRotHis_finalTangent(Vector3d transRotHis_finalTangent) {
		this.transRotHis_finalTangent = transRotHis_finalTangent;
	}

	public void setTransRotHis_devAngle(double transRotHis_devAngle) {
		this.transRotHis_devAngle = transRotHis_devAngle;
	}

	protected void setMaxStep(int maxStep) {
		MaxStep = maxStep;
	}
}