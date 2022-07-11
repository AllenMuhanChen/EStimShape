package org.xper.drawing.stick;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.FileWriter;
import java.util.Random;
import java.util.StringTokenizer;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;

//a class that describe a single tube component about a whole Match Stick
public class TubeComp
{
	// we can set it to be true, to skip jacob_check
	private boolean skipJacobInAnalysisPhase = false;
	private int label;
	private MAxisArc mAxisInfo = new MAxisArc();
	private double[][] radInfo = new double[3][2];
	private boolean branchUsed;
	private double[] radiusAcross = new double[52]; // the radius value at each mPts point
	private int connectType;
	private Point3d maxXYZ;
	private Point3d minXYZ;
	private boolean scaleOnce = true;

	private int maxStep = 51;



	private Point3d[] vect_info = new Point3d[2000]; // 2000 should be large enough to contain all pts
	private Vector3d[] normMat_info = new Vector3d[2000];
	private int[][] facInfo = new int[2800][3];

	private int nVect;
	private final int nFac = 2760; // this will always be true


	private int ringSample = 20;
	private int capSample = 10;
	private Point3d[][] ringPt = new Point3d[55][35];
	private Point3d[][] cap_poleN = new Point3d[15][35];
	private Point3d[][] cap_poleS = new Point3d[15][35];
	public TubeComp()
	{
		// init the facInfo
		setFacInfo(sampleFaceInfo.getFacInfo());

	}

	/**
		copy the whole class from an input class
	 */
	public void copyFrom( TubeComp in)
	{
		int i, j;
		setLabel(in.getLabel());
		getmAxisInfo().copyFrom( in.getmAxisInfo());
		for (i=0; i<3; i++)
			for (j=0; j<2; j++)
				getRadInfo()[i][j] = in.getRadInfo()[i][j];
		setBranchUsed(in.isBranchUsed());
		for (i=1; i<=51; i++)
			getRadiusAcross()[i] = in.getRadiusAcross()[i];
		setConnectType(in.getConnectType());
		setMaxXYZ(new Point3d(in.getMaxXYZ()));
		setMinXYZ(new Point3d(in.getMinXYZ()));

		// about vect, fac
		setnVect(in.getnVect());		
		for (i=1; i<=getnVect(); i++)
		{
			getVect_info()[i] = new Point3d( in.getVect_info()[i]);
			getNormMat_info()[i] = new Vector3d(in.getNormMat_info()[i]);			
		}
		// Fac Info is always fix 
		// seems not need to copy the ringPT, cap_poleNS , we'll see later
	}

	/**
	      Set the mAxisInfo it has, and if the branch is used or not.
	 */
	public void initSet(MAxisArc inArc, boolean b_used, int in_type)
	{
		int i, j;
		getmAxisInfo().copyFrom(inArc);
		setBranchUsed(b_used);
		setConnectType(in_type);
		for (i=0; i<3; i++)
			for (j=0; j<2; j++)
				getRadInfo()[i][j] = 100.0;

	}

	private boolean RadApplied_Factory_SUB_CheckJacob()
	{
		// for curvy medial axis, we want to check if it stand the Jacobian check
		// to make it easier, we will regenerate our mAxis shape on yz plane, 'cuz that will be easier to calculate some value
		int step;
		double nowu, now_angle, nextu, next_angle;
		double smallStep = 0.01;
		double angleExtend = getmAxisInfo().getAngleExtend();
		double rad = getmAxisInfo().getRad();
		double localArcLen, next_localArcLen;
		double a_fac, b_fac, c_fac;
		double now_rad, now_rad_du, next_rad, next_rad_du;
		double Jacob1, Jacob2;
		Vector3d bound1_du = new Vector3d(), bound2_du = new Vector3d();

		Point3d mPts = new Point3d(), next_mPts = new Point3d();
		Vector3d mTangent = new Vector3d(), next_mTangent = new Vector3d();
		Vector3d nowNormal = new Vector3d(), next_Normal = new Vector3d();

		Vector3d gradR = new Vector3d();
		double gradR_len;
		Vector3d boundNorm1 = new Vector3d();
		Vector3d boundNorm2 = new Vector3d();
		Point3d impBound1 = new Point3d();
		Point3d impBound2 = new Point3d();

		//variable about next	
		Vector3d next_gradR = new Vector3d();
		double next_gradR_len;
		Vector3d next_boundNorm1 = new Vector3d();
		Vector3d next_boundNorm2 = new Vector3d();
		Point3d next_impBound1 = new Point3d();
		Point3d next_impBound2 = new Point3d();


		// radius value calculation
		{
			double u = getRadInfo()[1][0], m = getRadInfo()[0][1];
			double n = getRadInfo()[1][1], q = getRadInfo()[2][1];
			double denom = u - u*u;
			a_fac = (u*q - u*m - n + m) / denom;
			b_fac = (n - m - u*u*q + u*u*m) / denom;
			c_fac = m;		
		}

		Transform3D transMat = new Transform3D();		
		AxisAngle4d axisInfo = new AxisAngle4d( 1, 0, 0, Math.PI * 0.5);;			
		transMat.setRotation(axisInfo);


		for (step = 1 ; step <=getMaxStep(); step++)
		{
			nowu = ((double)step-1) / ((double)getMaxStep()-1);


			now_angle = nowu * angleExtend - 0.5 * angleExtend;	


			mPts.set(0, rad * Math.cos(now_angle), rad* Math.sin(now_angle));
			mTangent.set(0, -angleExtend*rad*Math.sin(now_angle), angleExtend*rad*Math.cos(now_angle));	
			localArcLen = mTangent.length();
			mTangent.normalize();

			now_rad = a_fac * nowu * nowu + b_fac * nowu + c_fac;
			now_rad_du = a_fac * 2 * nowu + b_fac;

			nowNormal.set( mTangent);
			transMat.transform(nowNormal); // nowNormal is the 90 degree rotate from tangent ( rotate along plane normal)

			//System.out.println(gradR  + " scale with " + (now_rad_du / local_arcLen));
			gradR.scale((now_rad_du / localArcLen), mTangent);		   
			gradR_len = gradR.length();

			Vector3d neg_gradR = new Vector3d();
			neg_gradR.negate(gradR);
			Vector3d normal_scale = new Vector3d();
			normal_scale.scale( Math.sqrt( 1.0 - gradR_len * gradR_len), nowNormal);

			boundNorm1.add( neg_gradR , normal_scale);		   
			boundNorm2.sub( neg_gradR, normal_scale);		   
			impBound1.scaleAdd( now_rad, boundNorm1, mPts);// impBound1 = now_rad * bound_Norm1 + mpos
			impBound2.scaleAdd( now_rad, boundNorm2, mPts);

			if (nowu == 1.0) // can't go over 1.0
				smallStep = -0.01;
			nextu = nowu + smallStep;
			next_angle = nextu * angleExtend - 0.5 * angleExtend;
			next_mPts.set(0, rad * Math.cos(next_angle), rad* Math.sin(next_angle));
			next_mTangent.set(0, -angleExtend*rad*Math.sin(next_angle), angleExtend*rad*Math.cos(next_angle));	
			next_localArcLen = next_mTangent.length();
			next_mTangent.normalize();

			next_rad = a_fac * nextu * nextu + b_fac * nextu + c_fac;
			next_rad_du = a_fac * 2 * nextu + b_fac;

			next_Normal.set(next_mTangent);
			transMat.transform(next_Normal);

			next_gradR.scale((next_rad_du / next_localArcLen), next_mTangent);		   
			next_gradR_len = next_gradR.length();

			Vector3d next_neg_gradR = new Vector3d();
			next_neg_gradR.negate(next_gradR);
			Vector3d next_normal_scale = new Vector3d();
			next_normal_scale.scale( Math.sqrt( 1.0 - next_gradR_len * next_gradR_len), next_Normal);

			next_boundNorm1.add( next_neg_gradR , next_normal_scale);		   
			next_boundNorm2.sub( next_neg_gradR,  next_normal_scale);		   
			next_impBound1.scaleAdd( next_rad, next_boundNorm1, next_mPts);// impBound1 = now_rad * bound_Norm1 + mpos
			next_impBound2.scaleAdd( next_rad, next_boundNorm2, next_mPts);

			bound1_du.sub(next_impBound1, impBound1);
			bound1_du.scale(1.0/smallStep);
			bound2_du.sub(next_impBound2, impBound2);
			bound2_du.scale(1.0/smallStep);

			Jacob1 = bound1_du.dot(mTangent);
			Jacob2 = bound2_du.dot(mTangent);


			if (Jacob1 < 0.0001 || Jacob2 < 0.0001)
			{

				//System.out.println("\n\nimpBound1 " + impBound1);
				//System.out.println("next_impBound1 " + next_impBound1);
				//System.out.println(" bound1_du " + bound1_du);
				//System.out.println("tangent " + mTangent);
				//System.out.println("Jacob1 " + Jacob1);
				//			System.out.println("		Find out Jacobian error while generating tubular skin!");
				//System.out.println(Jacob1 + " " + Jacob2);
				return false;
			}

		}

		return true;
	}	
	/**
		Apply the tubular skin onto this Tube component, 
		Use the mAxisInfo + radInfo
	 */
	public boolean RadApplied_Factory()
	{
		// variable setup




		//variables will be used
		int  i, j;
		double nowu, now_rad, now_rad_du;
		double local_arcLen, gradR_len;
		Vector3d gradR = new Vector3d();

		Point3d mpos = new Point3d();

		Vector3d boundNorm1 = new Vector3d();
		Vector3d boundNorm2 = new Vector3d();
		Point3d impBound1 = new Point3d();
		Point3d impBound2 = new Point3d();
		Vector3d tangent = new Vector3d(), rotAxis = new Vector3d();
		Vector3d nowNormal = new Vector3d();
		Vector3d Normal_str8 = new Vector3d(0,0,0);
		Transform3D transMat = new Transform3D();

		Vector3d boundNorm1_uStart = new Vector3d();
		Vector3d boundNorm1_uEnd = new Vector3d();
		boolean needCheckJacob = false;
		double a_fac, b_fac, c_fac;
		if ( getmAxisInfo().getRad() < 10000)
		{
			needCheckJacob = true;
			// this skipJacob will only be true, if we called in the main
			// in this class
			if ( this.isSkipJacobInAnalysisPhase() == true)
				needCheckJacob = false;
			if (needCheckJacob == true)
				if ( this.RadApplied_Factory_SUB_CheckJacob() == false)
					return false;
		}
		// 1. calculate the radius function
		// this are the result I calculated by hand,
		// the main idea is that we know radius value at u= 0, u0, 1,-> we calcualte the quadratic function at all points
		{
			double u = getRadInfo()[1][0], m = getRadInfo()[0][1];
			double n = getRadInfo()[1][1], q = getRadInfo()[2][1];
			double denom = u - u*u;
			a_fac = (u*q - u*m - n + m) / denom;
			b_fac = (n - m - u*u*q + u*u*m) / denom;
			c_fac = m;
			// 			System.out.println( a_fac * u*u + b_fac * u + c_fac);
			// 			System.out.println("ori value " + radInfo[1][1]);
		}

		// 2. apply the radius value along the samplePts ( main torso)
		if (getmAxisInfo().getRad() < 10000) //determine the rotAxis
		{
			Vector3d temp1, temp2;
			temp1 = getmAxisInfo().getmTangent()[1]; // it is ok to write =, since we didn't chg temp1, temp2 value
			temp2 = getmAxisInfo().getmTangent()[26]; // in theory, any two tangent will work
			rotAxis.cross(temp1, temp2);
			rotAxis.normalize();		
			AxisAngle4d axisInfo = new AxisAngle4d( rotAxis, Math.PI * 0.5);			
			transMat.setRotation(axisInfo);
		}
		else
		{			
			Vector3d temp1 = getmAxisInfo().getmTangent()[1];
			//if (temp1.getX() == 0.0)
			//  	Normal_str8.set( 1.0, 0.0, 0.0);
			if ( temp1.x == 0.0)
				Normal_str8.set(1.0, 0.0, 0.0);
			else
			{
				//Normal_str8.set( temp1.getY(), -temp1.getX(), 0.0);
				Normal_str8.set( temp1.y, -temp1.x, 0.0);
				Normal_str8.normalize();
			}		
			rotAxis.cross(Normal_str8, temp1);
			rotAxis.normalize();
		}
		for (i=1; i<= getMaxStep(); i++)
		{
			nowu = ( (double)(i-1)) / ( (double) (getMaxStep()-1));
			mpos.set( getmAxisInfo().getmPts()[i]);
			tangent.set( getmAxisInfo().getmTangent()[i]);
			local_arcLen = getmAxisInfo().getLocalArcLen()[i];
			now_rad = a_fac * nowu * nowu + b_fac * nowu + c_fac;
			now_rad_du = a_fac * 2 * nowu + b_fac;

			this.getRadiusAcross()[i] = now_rad;
			if (getmAxisInfo().getRad() < 10000)
			{
				nowNormal.set( tangent);
				transMat.transform(nowNormal); // nowNormal is the 90 degree rotate from tangent ( rotate along plane normal)
			}
			else
				nowNormal.set( Normal_str8);

			//System.out.println(gradR  + " scale with " + (now_rad_du / local_arcLen));
			gradR.scale((now_rad_du / local_arcLen), tangent);		   
			gradR_len = gradR.length();
			//System.out.println(gradR);
			//System.out.println(gradR_len + " the length");
			if ( gradR_len > 1.0)
			{
				//System.out.println( "gradient is too large here....");
				return false; // can't generate this shape
			}
			Vector3d neg_gradR = new Vector3d();
			neg_gradR.negate(gradR);
			Vector3d normal_scale = new Vector3d();
			normal_scale.scale( Math.sqrt( 1.0 - gradR_len * gradR_len), nowNormal);

			boundNorm1.add( neg_gradR , normal_scale);		   
			boundNorm2.sub( neg_gradR, normal_scale);		   
			impBound1.scaleAdd( now_rad, boundNorm1, mpos);// impBound1 = now_rad * bound_Norm1 + mpos
			impBound2.scaleAdd( now_rad, boundNorm2, mpos);

			if (i == 1)
				boundNorm1_uStart.set( boundNorm1);
			if ( i == getMaxStep())
				boundNorm1_uEnd.set( boundNorm1);

			// draw the ring
			for (j=1; j<= getRingSample(); j++)
			{
				Vector3d nowvec = new Vector3d();
				double nowrot_deg = ( (double)(j-1) / (double)getRingSample() ) * 2 * Math.PI;
				nowvec = stickMath_lib.rotVecArAxis(boundNorm1, tangent, nowrot_deg); // this is 1 degree in radian		

				getRingPt()[i][j] = new Point3d();
				getRingPt()[i][j].scaleAdd( now_rad, nowvec, mpos);
			}

		}

		// 3. appy at the cap
		// 3.1 at North pole
		{

			// by calculating d1,d2,d3, determine which direction to rotate
			double d1, d2, d3;

			tangent.negate(getmAxisInfo().getmTangent()[1]);

			d1 = boundNorm1_uStart.angle(tangent);

			Vector3d nowvec = new Vector3d();

			nowvec = stickMath_lib.rotVecArAxis(boundNorm1_uStart, rotAxis, 0.016726646259972); // this is 1 degree in radian		
			d2 = nowvec.angle(tangent);

			nowvec = stickMath_lib.rotVecArAxis(boundNorm1_uStart, rotAxis, -0.016726646259972); // this is 1 degree in radian			
			d3 = nowvec.angle(tangent);
			double deg_sign =100.0;
			if (d2 < d1 )
				deg_sign = 1.0;
			else if ( d3 < d1)
				deg_sign = -1.0;
			//System.out.println(d1 + " " + d2 + " " + d3 + " deg sign " + deg_sign);

			if ( deg_sign == 100.0)
				System.out.println(" error while finding which way to rotate --north pole");

			double deg_span = d1;
			double deg;
			for ( j = 1 ; j <= getCapSample() ; j++)
			{
				deg = ((double)(j-1)/ (double)getCapSample()) *  deg_span * deg_sign;		   
				nowvec = stickMath_lib.rotVecArAxis(boundNorm1_uStart, rotAxis, deg);

				//System.out.println( "now vec new_ " + nowvec);
				Vector3d nowDirect = new Vector3d();

				nowDirect.scale( getRadInfo()[0][1], nowvec); // radInfo[0][1] is the rad at u == 0

				for ( i = 1 ; i <= getRingSample(); i++)
				{
					double nowrot_deg = ((double)(i-1) / (double)getRingSample()) * 2 * Math.PI; // In this formula, we don't eventually rotate to 2pi
					nowvec = stickMath_lib.rotVecArAxis(nowDirect, getmAxisInfo().getmTangent()[1], nowrot_deg);                      

					//DGdata(1).cap(j,i,:) = DGdata(1).mpos + nowvec; ( matlab format)
					getCap_poleN()[j][i] = new Point3d();
					getCap_poleN()[j][i].add( getmAxisInfo().getmPts()[1], nowvec);
				}   
			}

		}
		// 3.2 at South pole
		{
			// by calculating d1,d2,d3, determine which direction to rotate
			double d1, d2, d3;	
			tangent.set(getmAxisInfo().getmTangent()[51]);

			d1 = boundNorm1_uEnd.angle(tangent);

			Vector3d nowvec = new Vector3d();

			nowvec = stickMath_lib.rotVecArAxis(boundNorm1_uEnd, rotAxis, 0.016726646259972); // this is 1 degree in radian		
			d2 = nowvec.angle(tangent);

			nowvec = stickMath_lib.rotVecArAxis(boundNorm1_uEnd, rotAxis, -0.016726646259972); // this is 1 degree in radian			
			d3 = nowvec.angle(tangent);
			double deg_sign =100.0;
			if (d2 < d1 )
				deg_sign = 1.0;
			else if ( d3 < d1)
				deg_sign = -1.0;

			//System.out.println(d1 + " " + d2 + " " + d3 + " deg sign " + deg_sign);

			if ( deg_sign == 100.0)
				System.out.println(" error while finding which way to rotate -south pole");

			double deg_span = d1;
			double deg;
			for ( j = 1 ; j <= getCapSample() ; j++)
			{
				deg = ((double)(j-1)/ (double)getCapSample()) *  deg_span * deg_sign;		   
				nowvec = stickMath_lib.rotVecArAxis(boundNorm1_uEnd, rotAxis, deg);

				//System.out.println( "now vec new_ " + nowvec);
				Vector3d nowDirect = new Vector3d();

				nowDirect.scale( getRadInfo()[2][1], nowvec); // radInfo[0][1] is the rad at u == 0

				for ( i = 1 ; i <= getRingSample(); i++)
				{
					double nowrot_deg = ((double)(i-1) / (double)getRingSample()) * 2 * Math.PI; // In this formula, we don't eventually rotate to 2pi
					nowvec = stickMath_lib.rotVecArAxis(nowDirect, getmAxisInfo().getmTangent()[51], nowrot_deg);                      

					//DGdata(1).cap(j,i,:) = DGdata(1).mpos + nowvec; ( matlab format)
					getCap_poleS()[j][i] = new Point3d();
					getCap_poleS()[j][i].add( getmAxisInfo().getmPts()[51], nowvec);
				}   
			}

		}
		
		

		// 4. summarize the result into vect, normMat, fac format
		{
			int nowVect=1;
			// 1. tipNorth
			Point3d tip1 = new Point3d();
			tip1.scaleAdd( - getRadInfo()[0][1], getmAxisInfo().getmTangent()[1], getmAxisInfo().getmPts()[1]);		
			getVect_info()[nowVect] = new Point3d(tip1);
			getNormMat_info()[nowVect] = new Vector3d();
			getNormMat_info()[nowVect].negate( getmAxisInfo().getmTangent()[1]);
			nowVect++;
			// 2. cap_North
			for (i= getCapSample(); i>=1; i--)
				for (j=1; j<=getRingSample(); j++)
				{
					getVect_info()[nowVect] = new Point3d( getCap_poleN()[i][j]);
					getNormMat_info()[nowVect] = new Vector3d();
					getNormMat_info()[nowVect].sub( getCap_poleN()[i][j], getmAxisInfo().getmPts()[1]);
					getNormMat_info()[nowVect].normalize();
					nowVect++;
				}
			// 3. torsoRing
			for (i=2; i <= getMaxStep()-1; i++)
				for (j=1; j<=getRingSample(); j++)
				{
					getVect_info()[nowVect] = new Point3d( getRingPt()[i][j]);
					getNormMat_info()[nowVect] = new Vector3d();
					getNormMat_info()[nowVect].sub( getRingPt()[i][j], getmAxisInfo().getmPts()[i]);
					getNormMat_info()[nowVect].normalize();
					nowVect++;
				}
			// 4. cap_South
			for (i= 1; i<=getCapSample(); i++)
				for (j=1; j<=getRingSample(); j++)
				{
					getVect_info()[nowVect] = new Point3d( getCap_poleS()[i][j]);
					getNormMat_info()[nowVect] = new Vector3d();
					getNormMat_info()[nowVect].sub( getCap_poleS()[i][j], getmAxisInfo().getmPts()[51]);
					getNormMat_info()[nowVect].normalize();
					nowVect++;
				}
			// 5. tipSouth
			Point3d tip2 = new Point3d();
			tip2.scaleAdd( getRadInfo()[2][1], getmAxisInfo().getmTangent()[51], getmAxisInfo().getmPts()[51]);		
			getVect_info()[nowVect] = new Point3d(tip2);
			getNormMat_info()[nowVect] = new Vector3d(getmAxisInfo().getmTangent()[51]);

			//System.out.println("NOw Vect " + nowVect);
			this.setnVect(nowVect);
			// The fac_info could be retrived from pre-calculated data

		}

		// calculate the maxXYZ, and minXYZ
		this.calcTubeRange();
		return true;
	}
	public void calcTubeRange()
	{
		int i;	
		double maxX = -100.0, maxY = -100.0, maxZ = -100.0;
		double minX = 100.0, minY = 100.0, minZ = 100.0;

		for (i=1; i<= getnVect(); i++)
		{
			/*
			if (vect_info[i].getX() > maxX )
				maxX = vect_info[i].getX();
			if (vect_info[i].getY() > maxY )
				maxY = vect_info[i].getY();
			if (vect_info[i].getZ() > maxZ )
				maxZ = vect_info[i].getZ();
			if (vect_info[i].getX() < minX )
				minX = vect_info[i].getX();
			if (vect_info[i].getY() < minY )
				minY = vect_info[i].getY();
			if (vect_info[i].getZ() < minZ )
				minZ = vect_info[i].getZ();
			 */
			if (getVect_info()[i].x > maxX )
				maxX = getVect_info()[i].x;
			if (getVect_info()[i].y > maxY )
				maxY = getVect_info()[i].y;
			if (getVect_info()[i].z> maxZ )
				maxZ = getVect_info()[i].z;
			if (getVect_info()[i].x < minX )
				minX = getVect_info()[i].x;
			if (getVect_info()[i].y < minY )
				minY = getVect_info()[i].y;
			if (getVect_info()[i].z < minZ )
				minZ = getVect_info()[i].z;

		}


		setMaxXYZ(new Point3d(maxX, maxY, maxZ));
		setMinXYZ(new Point3d(minX, minY, minZ));
	}

	public void drawSurfPt(float[] colorCode, double scaleFactor)
	{
		//use the oGL draw line function to draw out the mAxisArc
		/*int ringSample = 20;
		  int capSample = 10;		
		  int maxStep = 51;*/
		if (isScaleOnce()) {
			scaleTheObj(scaleFactor);
			setScaleOnce(false);
		}

		boolean useLight = false;

		int i;
		GL11.glColor3f(0.0f, 1.0f, 0.0f);		    
		GL11.glPointSize(3.0f);	


		// draw the surface triangle
		if (useLight == false)
		{
			GL11.glDisable(GL11.GL_LIGHTING);
			GL11.glColor3f( colorCode[0], colorCode[1], colorCode[2]);
		}

		boolean drawMAxis = false;

		if (drawMAxis == true)
		{
			GL11.glLineWidth(5.0f);
			//GL11.gllin
			GL11.glBegin(GL11.GL_LINES);
			//GL11.glBegin(GL11.GL_POINTS);
			// Point3d p1 = this.mAxisInfo.transRotHis_finalPos;
			for (i=1; i<=50; i++)
			{
				Point3d p1 = this.getmAxisInfo().getmPts()[i];
				Point3d p2 = this.getmAxisInfo().getmPts()[i+1];
				GL11.glVertex3d( p1.x, p1.y, p1.z);
				GL11.glVertex3d(p2.x, p2.y, p2.z);
			}
			GL11.glEnd();
			GL11.glEnable(GL11.GL_LIGHTING);
			return;

		}
		
		GL11.glBegin(GL11.GL_TRIANGLES);
		//	GL11.glBegin(GL11.GL_POINTS);
		for (i=0; i< getnFac(); i++)
		{
			// 		System.out.println(i);
			// 		System.out.println("fac Info " + facInfo[i][0] +" " + facInfo[i][1] +" " + facInfo[i][2]);

			//AC TESTING
			Random r = new Random();
			GL11.glColor3f(r.nextFloat(), r.nextFloat(), r.nextFloat());
			Point3d p1 = getVect_info()[ getFacInfo()[i][0]];
			Point3d p2 = getVect_info()[ getFacInfo()[i][1]];
			Point3d p3 = getVect_info()[ getFacInfo()[i][2]];
			Vector3d v1 = getNormMat_info()[ getFacInfo()[i][0]];
			Vector3d v2 = getNormMat_info()[ getFacInfo()[i][1]];
			Vector3d v3 = getNormMat_info()[ getFacInfo()[i][2]];

			GL11.glNormal3d( v1.x, v1.y, v1.z);
			GL11.glVertex3d( p1.x, p1.y, p1.z);
			GL11.glNormal3d( v2.x, v2.y, v2.z);
			GL11.glVertex3d( p2.x, p2.y, p2.z);
			GL11.glNormal3d( v3.x, v3.y, v3.z);
			GL11.glVertex3d( p3.x, p3.y, p3.z);


		}

		GL11.glEnd();
		if ( useLight == false)
			GL11.glEnable(GL11.GL_LIGHTING);


		/*		
               GL11.glColor3f(0.0f, 1.0f, 0.0f);		    
	       for (i=1 ; i<= maxStep; i++)
	       {
		  GL11.glBegin(GL11.GL_POLYGON);
		  for (j=1; j<= ringSample; j++)
		  {

			Point3d nowPt = ringPt[i][j];
                  	GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());

                  }
		  GL11.glEnd();  
		}

               GL11.glColor3f(0.0f, 1.0f, 1.0f);		    
	       for (i=1 ; i<= capSample; i++)
	       {
		  GL11.glBegin(GL11.GL_POLYGON);
		  for (j=1; j<= ringSample; j++)
		  {

			Point3d nowPt = cap_poleN[i][j];
                  	GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());

                  }
		  GL11.glEnd();  
		}

               GL11.glColor3f(0.0f, 0.0f, 1.0f);		    
	       for (i=1 ; i<= capSample; i++)
	       {
		  GL11.glBegin(GL11.GL_POLYGON);
		  for (j=1; j<= ringSample; j++)
		  {

			Point3d nowPt = cap_poleS[i][j];
                  	GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());

                  }
		  GL11.glEnd();  
		}
		 */
		/*
		GL11.glPointSize(3.0f);	
   	      GL11.glBegin(GL11.GL_POINTS);
 	       for (i=1 ; i<= maxStep; i++)
		for (j=1; j<= ringSample; j++)
		{
			Point3d nowPt = ringPt[i][j];
                  	GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
                }  

	       for (i=1; i<=capSample; i++)
		for (j=1; j<=ringSample; j++)
		{
			GL11.glColor3f(0.0f, 1.0f, 1.0f);
			Point3d nowPt = cap_poleN[i][j];

			GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
			GL11.glColor3f(0.0f, 0.0f, 1.0f);
			Point3d nowPt2 = cap_poleS[i][j];
			GL11.glVertex3d(nowPt2.getX(), nowPt2.getY(), nowPt2.getZ());
                }

           	GL11.glEnd();
		 */
	}
	/**
		Translate the mAxisInfo and the vect_info to the new finalPos
	 */

	public void scaleTheObj(double scaleFactor)
	{
		int i;
		for (i=1; i<=getnVect(); i++)
		{
			getVect_info()[i].x *= scaleFactor;
			getVect_info()[i].y *= scaleFactor;
			getVect_info()[i].z *= scaleFactor;
		}
	}

	public void translateComp(Point3d finalPos)
	{
		int i;
//		System.out.println("AC 9958494: Im translating Comp");
		boolean showDebug = false;
		if ( showDebug)
			System.out.println("In translate components....");
		// make this.mAxisInfo.transRotHis_finalPos to new finalPos
		// 1. translate the mAxis arc related info
		Point3d oriPt = new Point3d(getmAxisInfo().getTransRotHis_finalPos());
		Vector3d transVec = new Vector3d();
		transVec.sub(finalPos, oriPt);

		getmAxisInfo().getTransRotHis_finalPos().set(finalPos);
		for (i=1; i<= getMaxStep(); i++)
		{
			getmAxisInfo().getmPts()[i].add(transVec);
		}

		// 2. translate the vect info
		// June 15th 2008, I suppose we can translate the vect_info directly, without taking care of the ringPt or PolePt info
		for (i=1; i <= getnVect(); i++)
		{
			getVect_info()[i].add(transVec);
		}
		calcTubeRange(); // the AABB of the tube is changed
	}

	public void showRadiusInfo()
	{
		int i;
		for (i=0; i<3; i++)			
		{
			System.out.println("	(u, r) = " + getRadInfo()[i][0] + " " + getRadInfo()[i][1]);
		}
	}


	// April 1st 2010
	// a function that can be called, w/ params
	// the effect is similar to main func
	// but we don't need to read/write a lot


	//July 22nd 2009
	// This is a main function that we are going to use to
	// generate a component by information from a file
	// and write out the polygon mesh result into another file
	public static void main(String[] args) {

		System.out.println("generate tube by file info...");

		Point3d finalPos = new Point3d(0,0,0); //always put at origin;
		Vector3d finalTangent = new Vector3d(0,0,0);	
		double devAngle = 0.0;
		int alignedPt = 26; // make it always the center of the mAxis curve


		// read the finalPos, finalTangent, curvature, ...from the file
		String fname = "./mAxisInput.txt";
		// read the file into a string 
		StringBuffer fileData = new StringBuffer(1000);
		try 
		{
			BufferedReader reader = new BufferedReader(
					new FileReader(fname));
			char[] buf = new char[1024];
			int numRead=0;
			while((numRead=reader.read(buf)) != -1){
				String readData = String.valueOf(buf, 0, numRead);
				fileData.append(readData);
				buf = new char[1024];	    		
			}
			reader.close();
		}
		catch (Exception e)    
		{
			System.out.println(e);
		}	    			
		String res = fileData.toString();
		StringTokenizer st = new StringTokenizer(res," ",false);
		String t="";
		int i=0;
		//double[] inputVec = new double[15];
		double[] totalInput = new double[20000];
		while (st.hasMoreElements())
		{

			t = "" + st.nextElement();
			//System.out.println("toke " + i + " :  " + t);
			//inputVec[i] = Double.parseDouble(t);
			totalInput[i] = Double.parseDouble(t);
			i++;
		}

		int j;
		int nEntries = i;
		int nSegment = nEntries / 15;
		System.out.println("nEntries: " + nEntries + " --> nSeg " + nSegment);
		TubeComp[] nowComp = new TubeComp[nSegment];

		for (i=0; i< nSegment; i++)
		{
			//inputVec has value from 0 ~11
			// 0~ 2 pos
			// 3 ~ 5 tangent Vec
			// 6 -> curvature
			// 7 -> arcLen
			// 8 -> devAngle
			// 9~ 13 -> r1, r2, r3 , rotCenter, alignedPt
			// 14 unitLength (not useful here)
			double[] inputVec = new double[15];
			for (j=0; j<15; j++)
				inputVec[j] = totalInput[i*15 + j];

			finalPos.set(inputVec[0], inputVec[1], inputVec[2]);
			finalTangent.set(inputVec[3], inputVec[4], inputVec[5]);
			double rad = 1.0/ inputVec[6];
			double arcLen = inputVec[7];			
			devAngle = inputVec[8];		
			double r1 = inputVec[9];
			double r2 = inputVec[10];
			double r3 = inputVec[11];
			Vector3d targetNormal = new Vector3d();
			targetNormal.x = inputVec[12];
			targetNormal.y = inputVec[13];
			targetNormal.z = inputVec[14];

			// 	Process the input parameters into a polygon mesh
			MAxisArc nowArc = new MAxisArc();
			nowArc.genArc(rad, arcLen);
			devAngle = 0.0; // since we want a precise rot, later;
			nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);						
			nowArc.deviateToTargetNormal(targetNormal);

			nowComp[i] = new TubeComp();
			nowComp[i].initSet( nowArc, false, 0); // the MAxisInfo, and the branchUsed



			nowComp[i].getRadInfo()[0][0] = 0.0;
			nowComp[i].getRadInfo()[0][1] = r1;
			nowComp[i].getRadInfo()[1][0] = 0.5;
			nowComp[i].getRadInfo()[1][1] = r2;
			nowComp[i].getRadInfo()[2][0] = 1.0;
			nowComp[i].getRadInfo()[2][1] = r3;

			//put in the nowComp radInfo;
			nowComp[i].setSkipJacobInAnalysisPhase(true);
			nowComp[i].RadApplied_Factory();
		} //for loop
		//then dump the vertex and fac info in nowComp 
		// 	to another file
		try{
			String foutname = "./mAxisOutput.txt";			
			BufferedWriter out = new BufferedWriter(new FileWriter(foutname));

			//write how many segments in this file
			out.write(nSegment + "\n");
			for (i=0; i< nSegment; i++)
			{
				//write the component surface structure to out3
				out.write( nowComp[i].getnVect() + "\n");								
				int it1, it2;

				for (it1 = 1; it1 <= nowComp[i].getnVect(); it1++)
				{

					out.write(nowComp[i].getVect_info()[it1].x + " " + nowComp[i].getVect_info()[it1].y + " " 
							+ nowComp[i].getVect_info()[it1].z +" ");

					out.write(nowComp[i].getNormMat_info()[it1].x + " " + nowComp[i].getNormMat_info()[it1].y +  " "
							+ nowComp[i].getNormMat_info()[it1].z + " \n");
				}
				out.write(nowComp[i].getnFac() +"\n");
				for (it1 = 0 ; it1 <nowComp[i].getnFac(); it1++)
				{
					for (it2 = 0; it2 <3; it2++)
					{							
						out.write(nowComp[i].getFacInfo()[it1][it2] + " ");
					}
					out.write("\n");
				}
				out.flush();
				out.close();
			}//loop i 


		} 
		catch (Exception e)
		{
			System.out.println(e);
		}
	}

	public double[][] getRadInfo() {
		return radInfo;
	}

	public void setRadInfo(double[][] radInfo) {
		this.radInfo = radInfo;
	}

	public int getLabel() {
		return label;
	}

	public void setLabel(int label) {
		this.label = label;
	}

	public MAxisArc getmAxisInfo() {
		return mAxisInfo;
	}

	public void setmAxisInfo(MAxisArc mAxisInfo) {
		this.mAxisInfo = mAxisInfo;
	}

	public boolean isBranchUsed() {
		return branchUsed;
	}

	public void setBranchUsed(boolean branchUsed) {
		this.branchUsed = branchUsed;
	}

	public double[] getRadiusAcross() {
		return radiusAcross;
	}

	public void setRadiusAcross(double[] radiusAcross) {
		this.radiusAcross = radiusAcross;
	}

	public int getConnectType() {
		return connectType;
	}

	public void setConnectType(int connectType) {
		this.connectType = connectType;
	}

	public Point3d getMaxXYZ() {
		return maxXYZ;
	}

	public void setMaxXYZ(Point3d maxXYZ) {
		this.maxXYZ = maxXYZ;
	}

	public Point3d getMinXYZ() {
		return minXYZ;
	}

	public void setMinXYZ(Point3d minXYZ) {
		this.minXYZ = minXYZ;
	}

	public int getnVect() {
		return nVect;
	}

	public void setnVect(int nVect) {
		this.nVect = nVect;
	}

	public Point3d[] getVect_info() {
		return vect_info;
	}

	public void setVect_info(Point3d[] vect_info) {
		this.vect_info = vect_info;
	}

	public Vector3d[] getNormMat_info() {
		return normMat_info;
	}

	public void setNormMat_info(Vector3d[] normMat_info) {
		this.normMat_info = normMat_info;
	}

	public int getMaxStep() {
		return maxStep;
	}

	public void setMaxStep(int maxStep) {
		this.maxStep = maxStep;
	}

	public int getRingSample() {
		return ringSample;
	}

	public void setRingSample(int ringSample) {
		this.ringSample = ringSample;
	}

	public Point3d[][] getRingPt() {
		return ringPt;
	}

	public void setRingPt(Point3d[][] ringPt) {
		this.ringPt = ringPt;
	}

	public int getCapSample() {
		return capSample;
	}

	public void setCapSample(int capSample) {
		this.capSample = capSample;
	}

	public Point3d[][] getCap_poleN() {
		return cap_poleN;
	}

	public void setCap_poleN(Point3d[][] cap_poleN) {
		this.cap_poleN = cap_poleN;
	}

	public Point3d[][] getCap_poleS() {
		return cap_poleS;
	}

	public void setCap_poleS(Point3d[][] cap_poleS) {
		this.cap_poleS = cap_poleS;
	}

	public boolean isScaleOnce() {
		return scaleOnce;
	}

	public void setScaleOnce(boolean scaleOnce) {
		this.scaleOnce = scaleOnce;
	}

	public int[][] getFacInfo() {
		return facInfo;
	}

	public void setFacInfo(int[][] facInfo) {
		this.facInfo = facInfo;
	}

	public boolean isSkipJacobInAnalysisPhase() {
		return skipJacobInAnalysisPhase;
	}

	public void setSkipJacobInAnalysisPhase(boolean skipJacobInAnalysisPhase) {
		this.skipJacobInAnalysisPhase = skipJacobInAnalysisPhase;
	}

	public int getnFac() {
		return nFac;
	}


}