package org.xper.allen.drawing.composition;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.drawing.stick.MAxisArc;
import org.xper.drawing.stick.TubeComp;
import org.xper.drawing.stick.sampleFaceInfo;

public class AllenTubeComp extends TubeComp{
	
	private AllenMAxisArc mAxisInfo = new AllenMAxisArc();
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

	/**
	copy the whole class from an input class
	 */
	public void copyFrom(AllenTubeComp in)
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

}
