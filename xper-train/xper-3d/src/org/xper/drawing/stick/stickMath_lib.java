package org.xper.drawing.stick;
// June 5th 2008
// A class that save some of my common use static function


import java.util.Date;
import java.util.Random;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
*   June 5th 2008 <br>
*   A static library class that storing common function I will use
*/
public class stickMath_lib
{
	
	/**
	 *    input the (theta,phi) sphere coordinate of two vector
	 *    we return the difference in theta and phi 
	 */
	public static double[] myAngleBtwPolarVec( double[] inVec1, double[] inVec2)
	{
		double[] res = new double[2];
		double angleDiff = Math.abs(  inVec1[0] - inVec2[0]);
		if (angleDiff > Math.PI)
			angleDiff -= 2 * Math.PI;
		else if (angleDiff < - Math.PI)
			angleDiff += 2 * Math.PI;
		angleDiff = Math.abs( angleDiff);
		
		res[0] = angleDiff;
		res[1] = Math.abs( inVec1[1] - inVec2[1]);
		
		return res;
	}
	
	/**
	 *    seperate myAngleBtwPolarVec into 2 seperate function for phi/theta
	 *    (this will make things faster?)
	 */
	public static double myAngleBtwPolarVec_2d( double inVec1, double inVec2)
	{
		double angleDiff = Math.abs(  inVec1 - inVec2);
		//System.out.println("debug " + inVec1 + " " + inVec2 + " " + angleDiff);
		if (angleDiff > Math.PI)
			angleDiff -= 2 * Math.PI;
		else if (angleDiff < - Math.PI)
			angleDiff += 2 * Math.PI;

		if (angleDiff > Math.PI) //sometimes we need to do it twice
			angleDiff -= 2 * Math.PI;
		else if (angleDiff < - Math.PI)
			angleDiff += 2 * Math.PI;
		
		angleDiff = Math.abs( angleDiff);
		
		return angleDiff;
	}
	
	public static double myAngleBtwPolarVec_depth( double inVec1, double inVec2)
	{
		
		return Math.abs( inVec1 - inVec2);
		
	}
	
	
	
	
	/**
	 *   The function that given two vector, will rotate first one to (1,0,0)
	 *   and return the rotated result of the second one
	 */
	
	public static Vector3d getT2VectorAfterRotateT1( Vector3d in_t1, Vector3d in_t2)
	{
		//these two lines are important, otherwise we'll change the input params
		Vector3d t1 = new Vector3d( in_t1);
		Vector3d t2 = new Vector3d( in_t2);
		
		/// 1. rotate to [0 0 1 ]
//		  Vector3d nowvec = new Vector3d(0,0,0);
		  Transform3D transMat = new Transform3D(); 	  
		  Vector3d oriVec = t1;
		  Vector3d goalVec = new Vector3d(0,1,0);
		  double Angle = oriVec.angle(goalVec);
	 	  Vector3d RotAxis = new Vector3d(0,0,0);
		  RotAxis.cross(oriVec,  goalVec);
		  RotAxis.normalize();
		  
		// some simple case
		  if ( Angle < 0.0002) // around 1 degree
		  {
			  //System.out.println("no rotation to [0 0 1] needed");
			  RotAxis = new Vector3d(0,1,0);
			  Angle = 0.0;
		  }
		  else if ( Math.abs(Angle - Math.PI) < 0.0002)
		  {
			  //System.out.println(" t1 is very close to (0,0, -1)");
			  RotAxis = new Vector3d(1,0,0); // rotate along x axis is fine
			  
		  }
		  
		  
		  // start the rotation!
		  
		  
		  AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
		  transMat.setRotation(axisInfo);
		  
		  transMat.transform(t1);
		  transMat.transform(t2);
		  
		  t2.normalize();
		  //System.out.println( "after rotation" + t1 + "    "  + t2);
			
		  return t2;
		
	}
	
     /**
     * Print out the debug Info
     * @param title the str want to show
     * @param var the variable want to show
     */ 
    public static void debugInfo( String title, String var)
    {
	System.out.println(title + " :  " +var);
    }
    // return a random UNIT vector ( with unit distribution)
    /**
	generate a random unit vector (uniform distribution on the ball)
    */
    public static Vector3d randomUnitVec()
     {
        Random rand = new Random();	
        
	double u = rand.nextDouble();
	double v = rand.nextDouble();
	double theta = 2 * Math.PI * u;
    double phi = Math.acos(2 * v -1);
	Vector3d res = new Vector3d( Math.cos(theta)* Math.sin(phi), Math.sin(theta)*Math.sin(phi), Math.cos(phi));
	return res;
         
     }
    /**
	Pick a index value from a pre-defined Prob distribution
	@param probDist CDF like {0.333, 0.6666, 1.000}
    */
    public static int pickFromProbDist(double[] probDist)
    {
	int i;
	Random rand = new Random();
	double rNDX = rand.nextDouble();
	int nRes = probDist.length;
	for (i=0; i< nRes; i++)
	{
		if (rNDX <= probDist[i])
			return (i+1);
	}
	// should not come here
	return -1;
	
    }
    /**
	function that return a rand value btw 0 and 1
    */
    public static double rand01()
    {
	Random rand = new Random();
	return rand.nextDouble();
    }
    /**
	return random value btw a and b ( float point value)
    */
    public static double randDouble(double a, double b)
    {
	Random rand = new Random();
	return rand.nextDouble() * (b-a) + a;
    }
    /**
	return random integer btw a and b ( including a and b)
    */

    /**
     * @author r2_allen
     * return random scalar between (1-b):(1-a) and (1+a):(1+b). 
     * @return
     */
    public static double randScalarInTails(double a, double b) {
    	if(rand01()<0.5) 
    		return 1 - randDouble(-b,-a);
    	else
    		return 1 + randDouble(a,b);
    			
    	
    }
    
    /** 
	function that calculate the 3D spatial rotation
	input are the vector to compute, the axis vector and the degree to rotate
    */
    public static Vector3d rotVecArAxis(Vector3d in_vec, Vector3d rot_Axis, double rot_deg)
    {
   		AxisAngle4d axisInfo = new AxisAngle4d( rot_Axis, rot_deg); // this is 1 degree in radian
		Transform3D transMat = new Transform3D();
		transMat.setRotation(axisInfo);
		Vector3d nowvec = new Vector3d( in_vec);		
                transMat.transform(nowvec);
                return nowvec;
    }

    public static int randInt(int a, int b)
    {
    	Random rand = new Random();
    	return rand.nextInt(b-a+1) + a;
    }

    
    /**
     *   function that rotate a Vector around origin.
     *   Same as rotatePointAroundOrigin
     */
    public static Vector3d rotateVectorAroundOrigin(Vector3d inPos, 
			double xdeg, double ydeg, double zdeg)
    {
    	Point3d nowPt = new Point3d(inPos);
    	Point3d resPt = rotatePointAroundOrigin(nowPt, xdeg, ydeg, zdeg);
    	Vector3d resVec = new Vector3d( resPt);
    	
    	return resVec;
    }
    
    /**
     *   function that rotate a point or vector around origin, with X deg, Y deg, Zdeg
     */
    
    public static Point3d rotatePointAroundOrigin(Point3d inPos, 
    								double xdeg, double ydeg, double zdeg)
    {
    	Point3d nowPt = new Point3d(inPos);
		// 1. rot X
		{
		   Vector3d RotAxis = new Vector3d(1,0,0);
		   double Angle = (xdeg /180.0 ) *Math.PI;
		   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
		   Transform3D transMat = new Transform3D();
		   transMat.setRotation(axisInfo);
		   transMat.transform(nowPt);			   		   
		} 
		// 2. rot Y
		{
		   Vector3d RotAxis = new Vector3d(0,1,0);
		   double Angle = (ydeg /180.0 ) *Math.PI;
		   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
		   Transform3D transMat = new Transform3D();
		   transMat.setRotation(axisInfo);
		   transMat.transform(nowPt);
		
		}
		
		// 3. rot Z
		{
			   Vector3d RotAxis = new Vector3d(0,0,1);
			   double Angle = (zdeg /180.0 ) *Math.PI;
			   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
			   Transform3D transMat = new Transform3D();
			   transMat.setRotation(axisInfo);			   
			   transMat.transform(nowPt);
			   
		}
		return nowPt;
    }
    
    public static Vector3d[] rotateVectorListAroundOrigin(int nPts, Vector3d[] inVec,
    		double xdeg, double ydeg, double zdeg)
    {
    	int i;
    	Point3d[] nowPts = new Point3d[nPts+1];
    	Vector3d[] resVec = new Vector3d[nPts+1];
    	for (i=1; i<=nPts; i++)    	
    		nowPts[i] = new Point3d( inVec[i]);
    	nowPts = rotatePointListAroundOrigin(nPts, nowPts, xdeg, ydeg, zdeg);
    	
    	for (i=1; i<=nPts; i++)
    		resVec[i] = new Vector3d( nowPts[i]);
    	
    	return resVec;
    	
    }
    
    /**
     *   function that rotate a point or vector around origin, with X deg, Y deg, Zdeg
     */
    
    public static Point3d[] rotatePointListAroundOrigin(int nPt, Point3d[] inPos, 
    								double xdeg, double ydeg, double zdeg)
    {
    	int i;
		// 1. rot X
		{
		   Vector3d RotAxis = new Vector3d(1,0,0);
		   double Angle = (xdeg /180.0 ) *Math.PI;
		   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
		   Transform3D transMat = new Transform3D();		   
		   transMat.setRotation(axisInfo);
		   for (i=1; i<=nPt; i++)		   
			   transMat.transform(inPos[i]);
		   
		} 
		// 2. rot Y
		{
		   Vector3d RotAxis = new Vector3d(0,1,0);
		   double Angle = (ydeg /180.0 ) *Math.PI;
		   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
		   Transform3D transMat = new Transform3D();
		   transMat.setRotation(axisInfo);
		   for (i=1; i<=nPt; i++)		   
			   transMat.transform(inPos[i]);
		   
		
		}
		
		// 3. rot Z
		{
			   Vector3d RotAxis = new Vector3d(0,0,1);
			   double Angle = (zdeg /180.0 ) *Math.PI;
			   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
			   Transform3D transMat = new Transform3D();
			   transMat.setRotation(axisInfo);			   
			
			   for (i=1; i<=nPt; i++)		   
				   transMat.transform(inPos[i]);
			   
		}
		return inPos;
    }
    
    
    /*
     *   
     */
    public static void waitKeyBoard()
    {    			
		try{
			
		    	System.out.println("Input any key with enter to continue...");			
		    	System.in.read(); // a way to halt the program to not stop
		}
		catch (Exception e) {}	
    }
    
    
    
    
    // Get the X, Y, or Z of a point3d structure
    
/**
    Main function for debug
*/
    public static void main(String[] args)
    {
    	Date test1 = new Date();
    	System.out.println(test1.toString());
    	Date test2 = new Date( test1.getTime());
    	System.out.println(test2);
    	System.out.println(test2.getTime());
    	System.out.println(test1.getTime());
    	Date test3 = new Date( 1L);
    	System.out.println(test3.getTime());
    	System.out.println(test3.toString());
    	
    	double[] probDist = {0.2, 0.4, 0.7, 1.0};
    	int i;
    	for (i=0; i<3; i++)
    		System.out.println( pickFromProbDist(probDist));
    	
    	// 
    }
    
}