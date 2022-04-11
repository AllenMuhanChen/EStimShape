package org.xper.allen.drawing.composition;

import java.util.Random;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.stick.MAxisArc;
import org.xper.drawing.stick.TubeComp;
import org.xper.drawing.stick.sampleFaceInfo;
import org.xper.util.ThreadUtil;

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
	// we can set it to be true, to skip jacob_check
	public boolean skipJacobInAnalysisPhase = false;
	private int label;
	private double[][] radInfo = new double[3][2];
	private boolean branchUsed;
	private double[] radiusAcross = new double[52]; // the radius value at each mPts point
	private int connectType;
	private Point3d maxXYZ;
	private Point3d minXYZ;
	boolean scaleOnce = true;
	private boolean isNormalized = false;
	public int maxStep = 51;



	private Point3d[] vect_info = new Point3d[2000]; // 2000 should be large enough to contain all pts
	private Vector3d[] normMat_info = new Vector3d[2000];
	private int[][] facInfo = new int[2800][3];

	private int nVect;
	public final int nFac = 2760; // this will always be true


	protected int ringSample = 20;
	protected int capSample = 10;
	protected Point3d[][] ringPt = new Point3d[55][35];
	protected Point3d[][] cap_poleN = new Point3d[15][35];
	protected Point3d[][] cap_poleS = new Point3d[15][35];
	public AllenTubeComp()
	{
		// init the facInfo
		setFacInfo(sampleFaceInfo.getFacInfo());

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
		setRingPt(in.getRingPt());
		setCap_poleN(in.getCap_poleN());
		setCap_poleS(in.getCap_poleS());
		setRingSample(in.getRingSample());
		setCapSample(in.getCapSample());
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
	
	public AllenMAxisArc getmAxisInfo() {
		return mAxisInfo;
	}

	public void setmAxisInfo(AllenMAxisArc mAxisInfo) {
		this.mAxisInfo = mAxisInfo;
	}

	public boolean isSkipJacobInAnalysisPhase() {
		return skipJacobInAnalysisPhase;
	}

	public void setSkipJacobInAnalysisPhase(boolean skipJacobInAnalysisPhase) {
		this.skipJacobInAnalysisPhase = skipJacobInAnalysisPhase;
	}

	public int getLabel() {
		return label;
	}

	public void setLabel(int label) {
		this.label = label;
	}

	public double[][] getRadInfo() {
		return radInfo;
	}

	public void setRadInfo(double[][] radInfo) {
		this.radInfo = radInfo;
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

	public boolean isScaleOnce() {
		return scaleOnce;
	}

	public void setScaleOnce(boolean scaleOnce) {
		this.scaleOnce = scaleOnce;
	}

	public int getMaxStep() {
		return maxStep;
	}

	public void setMaxStep(int maxStep) {
		this.maxStep = maxStep;
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

	public int[][] getFacInfo() {
		return facInfo;
	}

	public void setFacInfo(int[][] facInfo) {
		this.facInfo = facInfo;
	}

	public int getnVect() {
		return nVect;
	}

	public void setnVect(int nVect) {
		this.nVect = nVect;
	}

	public int getRingSample() {
		return ringSample;
	}

	public void setRingSample(int ringSample) {
		this.ringSample = ringSample;
	}

	public int getCapSample() {
		return capSample;
	}

	public void setCapSample(int capSample) {
		this.capSample = capSample;
	}

	public Point3d[][] getRingPt() {
		return ringPt;
	}

	public void setRingPt(Point3d[][] ringPt) {
		this.ringPt = ringPt;
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

	public int getnFac() {
		return nFac;
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
