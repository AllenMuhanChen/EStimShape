package org.xper.drawing.stick;

import java.util.Random;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.drawing.stick.stickMath_lib;

import org.lwjgl.opengl.GL11;

public class MAxisArc
{
     private final int MaxStep = 51;

     private double rad;

	public double curvature;
     private double arcLen;

	private double angleExtend;
     
     private int branchPt;
     private Point3d[] mPts= new Point3d[MaxStep+1];
     private Vector3d[] mTangent= new Vector3d[MaxStep+1];
     private double[] localArcLen = new double[MaxStep+1];

     private int transRotHis_alignedPt;

	private int transRotHis_rotCenter;
     private Point3d transRotHis_finalPos = new Point3d();
     private Vector3d transRotHis_finalTangent = new Vector3d();
     private double transRotHis_devAngle;

  

     public MAxisArc() {
		// this.rad = 100.0; //nothing, just debug
		 int i;
		 for (i=0; i<=MaxStep; i++) {
	           mPts[i] = new Point3d();
		       mTangent[i] = new Vector3d();
		 }
 	}
     

     
	public void copyFrom( MAxisArc in) {
		int i;
		setRad(in.getRad());
		curvature = in.curvature;
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
	}
     
	public void genSimilarArc( MAxisArc inArc,int alignedPt,  double volatileRate) {
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
	
	
	
	/**
	generate a new MAxis Arc, with radius and arcLen randomly chosen
	 */
	public void genArcRand()
	{
		// randomly determine the rad and arcLen, and then call genArc
		double RadView = 5.0;
		// high curvature 0.2 ~ 0.6 R
		// medium curvature 0.6 ~ 6 R
		// no curvautre, let k = 0.000001;
		double[] radDistribution = { .3333, .6666, 1}; // the cumulative prob for high, medium & no curvature

		Random rand = new Random();	
		double radRandNdx = rand.nextDouble();

		if (radRandNdx <= radDistribution[0] )
		{
			setRad((rand.nextDouble() * 0.4 + 0.2) * RadView); // btw (0.2 ~0.6)R      
			//disp 'pick high curvature';
		}
		else if (radRandNdx <= radDistribution[1])
		{
			setRad((rand.nextDouble() * 5.4 + 0.6) * RadView); // btw (0.6~6)R
			//disp 'pick medium curvature';
		}	
		else if (radRandNdx <= radDistribution[2])
		{
			setRad(100000);
			//disp 'pick no curvature';
		}


		//k = 1 / rad;

		// 2. choose the length
		double length_lb = 1.5; //the lower bound of length
		double length_ub = Math.min( Math.PI * getRad(), RadView);
		//pick a value btw length_lb & length_ub
		double arcLen = rand.nextDouble() * (length_ub - length_lb) + length_lb;

		// 	System.out.println("rad is : " + rad);	
		// 	System.out.println("arcLen is : " + arcLen);

		this.genArc(getRad(), arcLen);

	}
	/**
	generate a new MAxis Arc, with radius and arcLen defined
	@param in_rad the radius value wanted
	@param in_arcLen the arcLen value wanted
	 */
	public void genArc(double in_rad, double in_arcLen)
	{
		setRad(in_rad);
		setArcLen(in_arcLen);
		curvature = 1.0 / getRad();
		setAngleExtend(getArcLen() / getRad());

		//         System.out.println("in genArc  rad: "+ rad + " ArcLen: " + arcLen);
		int step;
		double nowu, now_angle;
		if ( getRad() >= 100000) //str8 line condition
		{
			for (step=1; step <=getMaxStep(); step++)
			{
				nowu = ((double)step-1) / ((double)getMaxStep()-1);

				getmPts()[step].set(0,0, nowu* getArcLen());
				getmTangent()[step].set(0,0,1);
				getLocalArcLen()[step] = getArcLen();      
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
				getmPts()[step].set(0, getRad() * Math.cos(now_angle), getRad()* Math.sin(now_angle));
				getmTangent()[step].set(0, -getAngleExtend()*getRad()*Math.sin(now_angle), getAngleExtend()*getRad()*Math.cos(now_angle));
				//System.out.println(mAxis_tangent[step]);
				getLocalArcLen()[step] = getmTangent()[step].length();
				getmTangent()[step].normalize();
				//System.out.println(mAxis_tangent[step] + "  len:  " + mAxis_arcLen[step]);
			}

		}

		// randomly assign a branchPt value at the middle of the samplePts
		// Matlab: resultArc.branchPt =  ceil( ( resultArc.nSamplePts-39) .* rand() ) + 20; % all the middle pts
		this.setBranchPt(stickMath_lib.randInt(26-5 , 26+5));


	}
	public void showInfo()
	{
		System.out.println("Info about MAxisArc:");
		System.out.println("rad : " + getRad());
		//show the mAxis pts
		System.out.println("transRot alignedPt :" + getTransRotHis_alignedPt());
		System.out.println("mpts[1] is at : "+ getmPts()[1]);
		System.out.println("tangent[1] is at : "+ getmTangent()[1]);
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
	 @param alignedPt integer, assign which point on mAxisArc to go to finalPos
	 @param finalPos Point3d, the final pos to align
	 @param rotCenter integer, the point play as center when rotate
	 @param finalTangent Vector3d, the tangent direction where the rotCenter Pt will face
	 @param deviateAngle double btw 0 ~ 2PI , the angle to rotate along the tangent direction
     */
     public void transRotMAxis(int alignedPt, Point3d finalPos, int rotCenter, Vector3d finalTangent, double deviateAngle)
     {
// 	System.out.println("transRot mAxis procedure:");
// 	System.out.println("final pos: "+finalPos + "final tangent: "+finalTangent);
	/// 1. rotate to [0 0 1]
	  int i;
	  Point3d oriPt = new Point3d();
	  Vector3d nowvec = new Vector3d(0,0,0);
	  Transform3D transMat = new Transform3D(); 	  
	  Vector3d oriTangent = getmTangent()[rotCenter];
	  Vector3d interTangent = new Vector3d(0,0,1);
	  double Angle = oriTangent.angle(interTangent);
 	  Vector3d RotAxis = new Vector3d(0,0,0);
	  RotAxis.cross(oriTangent, interTangent);
	  RotAxis.normalize();
//    System.out.println(oriTangent + " " + interTangent);
//    System.out.println(Angle);
//    System.out.println(RotAxis);

	  boolean skipRotate = false;
	  //July 24 2009, should we remove Angle == Math.PI
          if ( Angle == 0.0 || Angle == Math.PI) // no need to turn
	    //if (Angle == 0.0) // remove the Angle == Math.PI on July24 2009
	  {
      	     skipRotate = true;
// 		System.out.println("Skip first rotation");
// 		System.out.println("ori Tangent: " + oriTangent);
// 		System.out.println("inter tangent: " + interTangent);
// 		System.out.println("rad of the arc is " + rad);
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
			getmPts()[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt
			
             		// Original matlab code:    mPts[i] = (RotVecArAxe(nowvec', RotAxis', Angle))' + oriPt;             
             		// rotate the Tangent vector along the maxis
			transMat.transform(getmTangent()[i]);             		
       		}
	   }
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
      		oriPt.set(getmPts()[rotCenter]);
		AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
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
           }
//System.out.println("tangent[1] is at : "+ mTangent[1]);      
//System.out.println("mPts[1] is at : "+ mPts[1]);
	/// 3. rotate along the tangent axis by deviate Angle
	   if (  getRad() < 100000 ) // if the mAxisArc is a str8 line, no need to do this part
  	   {
   		oriPt.set(getmPts()[rotCenter]);
                AxisAngle4d axisInfo = new AxisAngle4d( finalTangent, deviateAngle);   		
		transMat.setRotation(axisInfo);
   		for (i = 1 ; i <= getMaxStep(); i++)
		{
			nowvec.sub(getmPts()[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
			transMat.transform(nowvec); 
			getmPts()[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt		
			         
			transMat.transform(getmTangent()[i]);             	             				
   		}
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
	   getTransRotHis_finalPos().set(finalPos);
	   //transRotHis_finalTangent = finalTangent;
	   getTransRotHis_finalTangent().set( finalTangent);
	   setTransRotHis_devAngle(deviateAngle);
//System.out.println("tangent[1] is at : "+ mTangent[1]);
     }

     /**
      *   July 24th 2009
      *   This function will make sure the normal vector at aligned Pt
      *   is matching to the targetNorm as the input params.
      *   This function will only be called in data analysis steps
      *  
      */
     public void deviateToTargetNormal( Vector3d TargetNorm)
     {
    	 if ( getRad() >= 100000) return; // striaght tube, no need to rotate
            	
    	 Transform3D transMat = new Transform3D();
    	 Transform3D transMat2 = new Transform3D();
    	 Vector3d nowvec = new Vector3d();
    	 int i;
    	 // 1. identify the current normalVector
    	 
    	 	Point3d endpt1 = this.getmPts()[1];
			Point3d endpt2 = this.getmPts()[51];
			Point3d midpt = this.getmPts()[26];
			Vector3d nowNorm= new Vector3d();
			nowNorm.x = endpt1.x + endpt2.x - midpt.x *2;
			nowNorm.y = endpt1.y + endpt2.y - midpt.y *2;
			nowNorm.z= endpt1.z + endpt2.z- midpt.z *2;
			nowNorm.normalize();
	
			Point3d oriPt = new Point3d();
			Vector3d finalTangent = new Vector3d();
			int rotCenter = 26; // when use this function, always rot at center
			finalTangent.set( getmTangent()[rotCenter]);
			oriPt.set(getmPts()[rotCenter]);
			
			double angle = nowNorm.angle(TargetNorm);
			
			// try positive_direction first
            AxisAngle4d axisInfo = new AxisAngle4d( finalTangent, angle);
            AxisAngle4d axisInfo2 =new AxisAngle4d( finalTangent, -angle);
            transMat.setRotation(axisInfo);
            transMat2.setRotation(axisInfo2);
            // check if the rotation direction is correct
            Vector3d testVec1 = new Vector3d(nowNorm);
            Vector3d testVec2 = new Vector3d(nowNorm);            
            transMat.transform(testVec1);
            transMat2.transform(testVec2);
            
            //show debug
            //System.out.println("original normal: " + nowNorm);
            //System.out.println("target normal:" + TargetNorm);
            //System.out.println("positive rot" + testVec1);
            //System.out.println("negative rot " + testVec2);
            
            if ( testVec1.angle(TargetNorm) < testVec2.angle(TargetNorm) )
            {
            		//System.out.println("choose positive rot");
            }
            else
            {
            		//System.out.println("choose negative rot");
            		transMat = transMat2;
            }
            
            for (i = 1 ; i <= getMaxStep(); i++)
            {
            	nowvec.sub(getmPts()[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
            	transMat.transform(nowvec); 
            	getmPts()[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt				         
            	transMat.transform(getmTangent()[i]);             	             				
            }
     }
     /**
	A function which can be called inside oGLFrame.display()
	This function will draw out the Arc in oGL window
     */
     public void drawArc()
     {
           //use the oGL draw line function to draw out the mAxisArc
	   int i;
           GL11.glColor3f(1.0f, 1.0f, 0.0f);
	   GL11.glBegin(GL11.GL_LINE_STRIP);
	   
 	    for (i=1; i<=getMaxStep(); i++)
		{
                  //GL11.glVertex3d(mPts[i].getX(), mPts[i].getY(), mPts[i].getZ());
 	    		GL11.glVertex3d( getmPts()[i].x, getmPts()[i].y, getmPts()[i].z);
		}  
             
           GL11.glEnd();

     }


	public int getMaxStep() {
		return MaxStep;
	}


	public Point3d[] getmPts() {
		return mPts;
	}


	public void setmPts(Point3d[] mPts) {
		this.mPts = mPts;
	}


	public Vector3d[] getmTangent() {
		return mTangent;
	}


	public void setmTangent(Vector3d[] mTangent) {
		this.mTangent = mTangent;
	}


	public double getRad() {
		return rad;
	}


	public void setRad(double rad) {
		this.rad = rad;
	}


	public Point3d getTransRotHis_finalPos() {
		return transRotHis_finalPos;
	}


	public void setTransRotHis_finalPos(Point3d transRotHis_finalPos) {
		this.transRotHis_finalPos = transRotHis_finalPos;
	}


	public int getTransRotHis_rotCenter() {
		return transRotHis_rotCenter;
	}


	public void setTransRotHis_rotCenter(int transRotHis_rotCenter) {
		this.transRotHis_rotCenter = transRotHis_rotCenter;
	}


	public Vector3d getTransRotHis_finalTangent() {
		return transRotHis_finalTangent;
	}


	public void setTransRotHis_finalTangent(Vector3d transRotHis_finalTangent) {
		this.transRotHis_finalTangent = transRotHis_finalTangent;
	}


	public double getTransRotHis_devAngle() {
		return transRotHis_devAngle;
	}


	public void setTransRotHis_devAngle(double transRotHis_devAngle) {
		this.transRotHis_devAngle = transRotHis_devAngle;
	}


	public int getTransRotHis_alignedPt() {
		return transRotHis_alignedPt;
	}


	public void setTransRotHis_alignedPt(int transRotHis_alignedPt) {
		this.transRotHis_alignedPt = transRotHis_alignedPt;
	}


	public double getArcLen() {
		return arcLen;
	}


	public void setArcLen(double arcLen) {
		this.arcLen = arcLen;
	}


	public int getBranchPt() {
		return branchPt;
	}


	public void setBranchPt(int branchPt) {
		this.branchPt = branchPt;
	}


	public double[] getLocalArcLen() {
		return localArcLen;
	}


	public void setLocalArcLen(double[] localArcLen) {
		this.localArcLen = localArcLen;
	}


	public double getAngleExtend() {
		return angleExtend;
	}


	public void setAngleExtend(double angleExtend) {
		this.angleExtend = angleExtend;
	}


}

