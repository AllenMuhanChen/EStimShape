package org.xper.allen.drawing.composition;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.noisy.NoiseMapCalculation;
import org.xper.drawing.stick.TubeComp;

/**
 * AC Additions:
 * AllenMAXisArc: keeps track of normal of devAngle along with new methods.
 * Normalized RadInfo: has additional fields to keep track of normalized RadInfo (between 0 and 1)
 * and a scale that when multiplied with normalized RadInfo yields unnormalized radInfo.
 * Has methods for generating and utilizing normalized RadInfo
 * @author r2_allen
 *
 */
public class AllenTubeComp extends TubeComp{

	private AllenMAxisArc mAxisInfo = new AllenMAxisArc();
	private double[][] normalizedRadInfo = new double[3][2];
	private double scale;
	private boolean isNormalized = false;



	public AllenTubeComp()
	{
		super();
	}

	//TODO: Figure out what to do with this.
	/**
	 * calculates the normalized radInfo information based on current radInfo.
	 */
	public void normalizeRadInfo() {
		double max = 0;
		for (int i=0; i<3; i++) {
			if (getRadInfo()[i][1] > max) {
				max = getRadInfo()[i][1];
			}
		}

		if(!isNormalized()) {
			for (int i=0; i<3; i++) {
				getNormalizedRadInfo()[i][0] = getRadInfo()[i][0];
				getNormalizedRadInfo()[i][1] = getRadInfo()[i][1] / max;
			}

			setScale(max);
			setNormalized(true);
		}
	}

	public void unnormalizeRadInfo() {
		for (int i=0; i<3; i++) {
			getRadInfo()[i][1] = getNormalizedRadInfo()[i][1] * scale;
		}
	}

	/**
	copy the whole class from an input class
	 */
	public void copyFrom(AllenTubeComp in)
	{
		int i, j;
		setLabel(in.getLabel());
		getmAxisInfo().copyFrom( in.getmAxisInfo());
		setScale(in.getScale());
		setNormalized(in.isNormalized());
		for (i=0; i<3; i++)
			for (j=0; j<2; j++) {
				getRadInfo()[i][j] = in.getRadInfo()[i][j];
				getNormalizedRadInfo()[i][j] = in.getNormalizedRadInfo()[i][j];
			}
		setBranchUsed(in.isBranchUsed());
		for (i=1; i<=51; i++)
			getRadiusAcross()[i] = in.getRadiusAcross()[i];
		setConnectType(in.getConnectType());
		if (in.getMaxXYZ() != null) {
			setMaxXYZ(new Point3d(in.getMaxXYZ()));
		}
		else{
			in.calcTubeRange();
			setMaxXYZ(new Point3d(in.getMaxXYZ()));
		}
		if (in.getMinXYZ() != null) {
			setMinXYZ(new Point3d(in.getMinXYZ()));
		} else {
			in.calcTubeRange();
			setMinXYZ(new Point3d(in.getMinXYZ()));
		}

		// about vect, fac
		setnVect(in.getnVect());
		for (i=1; i<=getnVect(); i++)
		{
			getVect_info()[i] = new Point3d( in.getVect_info()[i]);
			getNormMat_info()[i] = new Vector3d(in.getNormMat_info()[i]);
		}

		setScaleOnce(in.isScaleOnce()); //AC Addition when switched over to location relative to RFs, which
		// required not scaling the vect_info when doing morphs.


		// Fac Info is always fix
		// seems not need to copy the ringPT, cap_poleNS , we'll see later
//		setRingPt(in.getRingPt());
//		setCap_poleN(in.getCap_poleN());
//		setCap_poleS(in.getCap_poleS());
//		setRingSample(in.getRingSample());
//		setCapSample(in.getCapSample());
	}


	public void translateVectInfo(Point3d finalPos)
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



		// 2. translate the vect info
		// June 15th 2008, I suppose we can translate the vect_info directly, without taking care of the ringPt or PolePt info
		for (i=1; i <= getnVect(); i++)
		{
			getVect_info()[i].add(transVec);
		}
		calcTubeRange(); // the AABB of the tube is changed
	}

	/**
    Set the mAxisInfo it has, and if the branch is used or not.
	 */
	public void initSet(AllenMAxisArc inArc, boolean b_used, int in_type)
	{
		int i, j;
		getmAxisInfo().copyFrom(inArc);
		setBranchUsed(b_used);
		setConnectType(in_type);
		for (i=0; i<3; i++)
			for (j=0; j<2; j++)
				getRadInfo()[i][j] = 100.0;

	}

	public void scaleTheRing(double scaleFactor) {
		//AC
		System.out.println("AC MAXSTEP: " + getMaxStep());
		for(int i=1; i<=getMaxStep(); i++) {
			for(int j=1; j<getRingSample(); j++) {
				System.out.println("i: " + i + " j: " + j);
				getRingPt()[i][j].x *= scaleFactor;
				getRingPt()[i][j].y *= scaleFactor;
				getRingPt()[i][j].z *= scaleFactor;
			}
		}

		for (int i=1 ; i<= getCapSample(); i++)
		{
			for (int j=1; j<= getRingSample(); j++)
			{
				getCap_poleN()[i][j].x *= scaleFactor;
				getCap_poleN()[i][j].y *= scaleFactor;
				getCap_poleN()[i][j].z *= scaleFactor;

				getCap_poleS()[i][j].x *= scaleFactor;
				getCap_poleS()[i][j].y *= scaleFactor;
				getCap_poleS()[i][j].z *= scaleFactor;
			}

		}
	}

	public Point3d getMassCenter(){
		Point3d massCenter = new Point3d();
		for (int i=1; i<=getnVect(); i++)
		{
			massCenter.x += getVect_info()[i].x;
			massCenter.y += getVect_info()[i].y;
			massCenter.z += getVect_info()[i].z;
		}
		massCenter.x /= getnVect();
		massCenter.y /= getnVect();
		massCenter.z /= getnVect();
		return massCenter;

	}

	/**
	 * This is a corrected version of the function that corrects for a final position of the object.
	 * Previously, the scaling function here would amplify the any translation of the final position.
	 * Here, the shiftVec is undone first, then the scaling is applied, then the shiftVec is reapplied.
	 * @param colorCode
	 * @param scaleFactor
	 */
	public void drawSurfPt(float[] colorCode, double scaleFactor)
	{
		//use the oGL draw line function to draw out the mAxisArc
		/*int ringSample = 20;
		  int capSample = 10;
		  int maxStep = 51;*/

		if (isScaleOnce()) {
			System.out.println("AC: Scaling the object");
			scaleTheObj(scaleFactor);
			setScaleOnce(false);
		}


		boolean useLight = true;

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
//			Random r = new Random();
			GL11.glColor3f(colorCode[0], colorCode[1], colorCode[2]);
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




	}
	/**
	 Translate the mAxisInfo and the vect_info to the new finalPos
	 */


	public void drawSurfPt(double scaleFactor, NoiseMapCalculation noiseMap)
	{
		//use the oGL draw line function to draw out the mAxisArc
		/*int ringSample = 20;
		  int capSample = 10;
		  int maxStep = 51;*/
		if (isScaleOnce()) {
			scaleTheObj(scaleFactor);
			setScaleOnce(false);
		}
//		if (isScaleOnce()) {
//			scaleTheRing(scaleFactor);
//			setScaleOnce(false);
//		}


		boolean useLight = false;

		int i;
		GL11.glColor3f(0.0f, 1.0f, 0.0f);
		GL11.glPointSize(3.0f);


		// draw the surface triangle
		if (useLight == false)
		{
			GL11.glDisable(GL11.GL_LIGHTING);
		}



		boolean drawMAxis = false;

		if (drawMAxis == true)
		{
			GL11.glLineWidth(5.0f);
			//GL11.gllin
			GL11.glBegin(GL11.GL_LINES);
			//GL11.glBegin(GL11.GL_POINTS);
			// Point3d p1 = this.mAxisInfo.transRotHis_finalPos;
			Point3d[] upSampledMAxis = getmAxisInfo().constructUpSampledMpts(255);
			for (i=1; i<=254; i++)
			{
				Point3d p1 = upSampledMAxis[i];
				Point3d p2 = upSampledMAxis[i+1];
				GL11.glVertex3d( p1.x*scaleFactor, p1.y*scaleFactor, 0);
				GL11.glVertex3d(p2.x*scaleFactor, p2.y*scaleFactor, 0);
			}
//			GL11.glColor3f(0.f,0.f, 1.f);
//			for (i=1; i<=50; i++)
//			{
//				Point3d p1 = getmAxisInfo().getmPts()[i];
//				Point3d p2 = getmAxisInfo().getmPts()[i+1];
//				GL11.glVertex3d( p1.x*scaleFactor, p1.y*scaleFactor, p1.z*scaleFactor);
//				GL11.glVertex3d(p2.x*scaleFactor, p2.y*scaleFactor, p2.z*scaleFactor);
//			}
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
//			Random r = new Random();


			Point3d p1 = getVect_info()[ getFacInfo()[i][0]];
			Point3d p2 = getVect_info()[ getFacInfo()[i][1]];
			Point3d p3 = getVect_info()[ getFacInfo()[i][2]];
			Point3d[] triangleVertices = new Point3d[]{p1, p2, p3};
			float noiseChance = noiseMap.calculateNoiseChanceForTriangle(triangleVertices, getLabel(), scaleFactor);
			GL11.glColor3f(noiseChance, 0.0f, 0.f);
//			GL11.glColor3f(r.nextFloat(), r.nextFloat(), r.nextFloat());
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



//		ThreadUtil.sleep(1000);

//		int glMode = GL11.GL_POLYGON;
//		Random r = new Random();
////		GL11.glColor3f(0.0f, 1.0f, 0.0f);
//		for (i=1 ; i<= getMaxStep(); i++)
//		{
//			GL11.glColor3f(r.nextFloat(), r.nextFloat(), r.nextFloat());
//			GL11.glBegin(glMode);
//			for (int j=1; j<= getRingSample(); j++)
//			{
//				Point3d nowPt = getRingPt()[i][j];
//				GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
//
//			}
//			GL11.glEnd();
//		}
//
////		GL11.glColor3f(0.0f, 1.0f, 1.0f);
//
//		for (i=1 ; i<= getCapSample(); i++)
//		{
//			GL11.glColor3f(r.nextFloat(), r.nextFloat(), r.nextFloat());
//			GL11.glBegin(glMode);
//			for (int j=1; j<= getRingSample(); j++)
//			{
//
//				Point3d nowPt = getCap_poleN()[i][j];
//				GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
//
//			}
//			GL11.glEnd();
//		}
//
////		GL11.glColor3f(0.0f, 0.0f, 1.0f);
//
//		for (i=1 ; i<= getCapSample(); i++)
//		{
//			GL11.glColor3f(r.nextFloat(), r.nextFloat(), r.nextFloat());
//			GL11.glBegin(glMode);
//			for (int j=1; j<= getRingSample(); j++)
//			{
//
//				Point3d nowPt = getCap_poleS()[i][j];
//				GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
//
//			}
//			GL11.glEnd();
//		}

//
//		GL11.glPointSize(3.0f);
//		GL11.glBegin(GL11.GL_POINTS);
//		for (i=1 ; i<= maxStep; i++)
//			for (int j=1; j<= ringSample; j++)
//			{
//				Point3d nowPt = ringPt[i][j];
//				GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
//			}
//
//		for (i=1; i<=capSample; i++)
//			for (int j=1; j<=ringSample; j++)
//			{
//				GL11.glColor3f(0.0f, 1.0f, 1.0f);
//				Point3d nowPt = cap_poleN[i][j];
//
//				GL11.glVertex3d(nowPt.getX(), nowPt.getY(), nowPt.getZ());
//				GL11.glColor3f(0.0f, 0.0f, 1.0f);
//				Point3d nowPt2 = cap_poleS[i][j];
//				GL11.glVertex3d(nowPt2.getX(), nowPt2.getY(), nowPt2.getZ());
//			}
//
//		GL11.glEnd();

	}

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

	public AllenMAxisArc getmAxisInfo() {
		return mAxisInfo;
	}

	public void setmAxisInfo(AllenMAxisArc mAxisInfo) {
		this.mAxisInfo = mAxisInfo;
	}

	public double[][] getNormalizedRadInfo() {
		return normalizedRadInfo;
	}

	public void setNormalizedRadInfo(double[][] normalizedRadInfo) {
		this.normalizedRadInfo = normalizedRadInfo;
	}

	public double getScale() {
		return scale;
	}

	public void setScale(double scale) {
		this.scale = scale;
	}

	boolean isNormalized() {
		return isNormalized;
	}

	void setNormalized(boolean isNormalized) {
		this.isNormalized = isNormalized;
	}



}