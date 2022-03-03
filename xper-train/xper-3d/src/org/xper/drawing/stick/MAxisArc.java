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

     public double rad, curvature;
     public double arcLen, angleExtend;
     
     public int branchPt;
     public Point3d[] mPts= new Point3d[MaxStep+1];
     public Vector3d[] mTangent= new Vector3d[MaxStep+1];
     public double[] localArcLen = new double[MaxStep+1];

     public int transRotHis_alignedPt, transRotHis_rotCenter;
     public Point3d transRotHis_finalPos = new Point3d();
     public Vector3d transRotHis_finalTangent = new Vector3d();
     public double transRotHis_devAngle;


     public MAxisArc() {
		 rad = 100.0; //nothing, just debug
		 int i;
		 for (i=0; i<=MaxStep; i++) {
	           mPts[i] = new Point3d();
		       mTangent[i] = new Vector3d();
		 }
 	}

     
	public void copyFrom( MAxisArc in) {
		int i;
		rad = in.rad;
		curvature = in.curvature;
		arcLen = in.arcLen;
		angleExtend = in.angleExtend;
		branchPt = in.branchPt;
		for (i=1; i<= MaxStep; i++) {
			mPts[i].set( in.mPts[i]);
			mTangent[i].set( in.mTangent[i]);
			localArcLen[i] = in.localArcLen[i];
		}

		transRotHis_alignedPt = in.transRotHis_alignedPt;
		transRotHis_rotCenter = in.transRotHis_rotCenter;
		transRotHis_finalPos.set( in.transRotHis_finalPos);
		transRotHis_finalTangent.set( in.transRotHis_finalTangent);
		transRotHis_devAngle = in.transRotHis_devAngle;
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
// 	Point3d finalPos = new Point3d(0.0,0.0,0.0);
// 	this.transRotMAxis( 26, finalPos, inArc.transRotHis_rotCenter, newTangent, newDevAngle);

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
      		rad = (rand.nextDouble() * 0.4 + 0.2) * RadView; // btw (0.2 ~0.6)R      
      		//disp 'pick high curvature';
        }
        else if (radRandNdx <= radDistribution[1])
        {
      		rad = (rand.nextDouble() * 5.4 + 0.6) * RadView; // btw (0.6~6)R
      		//disp 'pick medium curvature';
        }	
        else if (radRandNdx <= radDistribution[2])
        {
      		rad = 100000;
      		//disp 'pick no curvature';
        }
  

	//k = 1 / rad;

        // 2. choose the length
  	double length_lb = 1.5; //the lower bound of length
  	double length_ub = Math.min( Math.PI * rad, RadView);
        //pick a value btw length_lb & length_ub
  	double arcLen = rand.nextDouble() * (length_ub - length_lb) + length_lb;

// 	System.out.println("rad is : " + rad);	
// 	System.out.println("arcLen is : " + arcLen);

	this.genArc(rad, arcLen);

     }
     /**
	generate a new MAxis Arc, with radius and arcLen defined
	@param in_rad the radius value wanted
	@param in_arcLen the arcLen value wanted
     */
     public void genArc(double in_rad, double in_arcLen)
     {
	rad = in_rad;
	arcLen = in_arcLen;
	curvature = 1.0 / rad;
	angleExtend = arcLen / rad;
	
//         System.out.println("in genArc  rad: "+ rad + " ArcLen: " + arcLen);
	int step;
	double nowu, now_angle;
	if ( rad >= 100000) //str8 line condition
	{
	   for (step=1; step <=MaxStep; step++)
	   {
		nowu = ((double)step-1) / ((double)MaxStep-1);
		
		mPts[step].set(0,0, nowu* arcLen);
		mTangent[step].set(0,0,1);
      		localArcLen[step] = arcLen;      
           }
        }
	else
 	{
	   for (step = 1 ; step <=MaxStep; step++)
 	   {
		nowu = ((double)step-1) / ((double)MaxStep-1);
		now_angle = nowu * angleExtend - 0.5 * angleExtend;
//	 System.out.println("step " + step+ " now u " + nowu + " angle " + now_angle);
//	 System.out.println(rad*Math.cos(now_angle));
//	 System.out.println(rad*Math.sin(now_angle));
//	 System.out.println(mAxis_pts.length);
		mPts[step].set(0, rad * Math.cos(now_angle), rad* Math.sin(now_angle));
		mTangent[step].set(0, -angleExtend*rad*Math.sin(now_angle), angleExtend*rad*Math.cos(now_angle));
	//System.out.println(mAxis_tangent[step]);
		localArcLen[step] = mTangent[step].length();
		mTangent[step].normalize();
	//System.out.println(mAxis_tangent[step] + "  len:  " + mAxis_arcLen[step]);
	   }

        }

         // randomly assign a branchPt value at the middle of the samplePts
           // Matlab: resultArc.branchPt =  ceil( ( resultArc.nSamplePts-39) .* rand() ) + 20; % all the middle pts
         this.branchPt = stickMath_lib.randInt(26-5 , 26+5);
	

     }
     public void showInfo()
     {
	System.out.println("Info about MAxisArc:");
	System.out.println("rad : " + rad);
	//show the mAxis pts
	System.out.println("transRot alignedPt :" + transRotHis_alignedPt);
	System.out.println("mpts[1] is at : "+ mPts[1]);
	System.out.println("tangent[1] is at : "+ mTangent[1]);
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
	  Vector3d oriTangent = mTangent[rotCenter];
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
      		oriPt.set(mPts[rotCenter]);
		AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
		transMat.setRotation(axisInfo);
       		for (i = 1 ; i <= MaxStep; i++)
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
  
      		for (i = 1 ; i <= MaxStep; i++)
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
//System.out.println("tangent[1] is at : "+ mTangent[1]);      
//System.out.println("mPts[1] is at : "+ mPts[1]);
	/// 3. rotate along the tangent axis by deviate Angle
	   if (  rad < 100000 ) // if the mAxisArc is a str8 line, no need to do this part
  	   {
   		oriPt.set(mPts[rotCenter]);
                AxisAngle4d axisInfo = new AxisAngle4d( finalTangent, deviateAngle);   		
		transMat.setRotation(axisInfo);
   		for (i = 1 ; i <= MaxStep; i++)
		{
			nowvec.sub(mPts[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
			transMat.transform(nowvec); 
			mPts[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt		
			         
			transMat.transform(mTangent[i]);             	             				
   		}
	   }
   //System.out.println("tangent[1] is at : "+ mTangent[1]);
//System.out.println("mPts[1] is at : "+ mPts[1]);
	/// 4. translation
	   oriPt.set( mPts[alignedPt]);
	   Vector3d transVec = new Vector3d(0,0,0);
	   transVec.sub(finalPos, oriPt);
	   for (i=1; i<=MaxStep; i++)
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
	   transRotHis_devAngle = deviateAngle;
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
    	 if ( rad >= 100000) return; // striaght tube, no need to rotate
            	
    	 Transform3D transMat = new Transform3D();
    	 Transform3D transMat2 = new Transform3D();
    	 Vector3d nowvec = new Vector3d();
    	 int i;
    	 // 1. identify the current normalVector
    	 
    	 	Point3d endpt1 = this.mPts[1];
			Point3d endpt2 = this.mPts[51];
			Point3d midpt = this.mPts[26];
			Vector3d nowNorm= new Vector3d();
			nowNorm.x = endpt1.x + endpt2.x - midpt.x *2;
			nowNorm.y = endpt1.y + endpt2.y - midpt.y *2;
			nowNorm.z= endpt1.z + endpt2.z- midpt.z *2;
			nowNorm.normalize();
	
			Point3d oriPt = new Point3d();
			Vector3d finalTangent = new Vector3d();
			int rotCenter = 26; // when use this function, always rot at center
			finalTangent.set( mTangent[rotCenter]);
			oriPt.set(mPts[rotCenter]);
			
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
            
            for (i = 1 ; i <= MaxStep; i++)
            {
            	nowvec.sub(mPts[i] , oriPt); // i.e. nowvec = mPts[i] - oriPt
            	transMat.transform(nowvec); 
            	mPts[i].add( nowvec , oriPt); // i.e mPts[i] = nowvec + oriPt				         
            	transMat.transform(mTangent[i]);             	             				
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
	   
 	    for (i=1; i<=MaxStep; i++)
		{
                  //GL11.glVertex3d(mPts[i].getX(), mPts[i].getY(), mPts[i].getZ());
 	    		GL11.glVertex3d( mPts[i].x, mPts[i].y, mPts[i].z);
		}  
             
           GL11.glEnd();

     }


}

