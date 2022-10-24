package org.xper.allen.drawing.composition;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *   class that store the information about a single tube
 *   The info include the MAxis and also the radius quadratic function.
 */
public class AllenTubeInfo
{
    private boolean branchUsed;
    private int connectType;
    private double[][] radInfo = new double[3][2];

    private double mAxis_rad;
    private double mAxis_arcLen; // only these two are important
                                //curvature & angleExtend can be calculated
    private int mAxis_branchPt;

    private int transRotHis_alignedPt;
    private int transRotHis_rotCenter;
    private Point3d transRotHis_finalPos;
    private Vector3d transRotHis_finalTangent;
    private double transRotHis_devAngle;
    
    private Vector3d curvatureNormal;
    
    public void setTubeInfo(AllenTubeComp inTube)
    {
        int i, j;
        this.setBranchUsed(inTube.isBranchUsed());
        this.setConnectType(inTube.getConnectType());
        for (i=0; i<3; i++)
            for (j=0; j<2; j++)
                this.getRadInfo()[i][j] = inTube.getRadInfo()[i][j];

        //mAxis related
        this.setmAxis_arcLen(inTube.getmAxisInfo().getArcLen());
        this.setmAxis_rad(inTube.getmAxisInfo().getRad());
        this.setmAxis_branchPt(inTube.getmAxisInfo().getBranchPt());

        //mAxis transRotHis related
        this.setTransRotHis_alignedPt(inTube.getmAxisInfo().getTransRotHis_alignedPt());
        this.setTransRotHis_rotCenter(inTube.getmAxisInfo().getTransRotHis_rotCenter());
        this.setTransRotHis_finalPos(new Point3d(inTube.getmAxisInfo().getTransRotHis_finalPos()));
        this.setTransRotHis_finalTangent(new Vector3d(inTube.getmAxisInfo().getTransRotHis_finalTangent()));
        this.setTransRotHis_devAngle(inTube.getmAxisInfo().getTransRotHis_devAngle());

        //Added by AC
        this.setCurvatureNormal(inTube.getmAxisInfo().getNormal());
    }

	public boolean isBranchUsed() {
		return branchUsed;
	}

	public void setBranchUsed(boolean branchUsed) {
		this.branchUsed = branchUsed;
	}

	public int getConnectType() {
		return connectType;
	}

	public void setConnectType(int connectType) {
		this.connectType = connectType;
	}

	public double[][] getRadInfo() {
		return radInfo;
	}

	public void setRadInfo(double[][] radInfo) {
		this.radInfo = radInfo;
	}

	public double getmAxis_arcLen() {
		return mAxis_arcLen;
	}

	public void setmAxis_arcLen(double mAxis_arcLen) {
		this.mAxis_arcLen = mAxis_arcLen;
	}

	public double getmAxis_rad() {
		return mAxis_rad;
	}

	public void setmAxis_rad(double mAxis_rad) {
		this.mAxis_rad = mAxis_rad;
	}

	public int getmAxis_branchPt() {
		return mAxis_branchPt;
	}

	public void setmAxis_branchPt(int mAxis_branchPt) {
		this.mAxis_branchPt = mAxis_branchPt;
	}

	public int getTransRotHis_alignedPt() {
		return transRotHis_alignedPt;
	}

	public void setTransRotHis_alignedPt(int transRotHis_alignedPt) {
		this.transRotHis_alignedPt = transRotHis_alignedPt;
	}

	public int getTransRotHis_rotCenter() {
		return transRotHis_rotCenter;
	}

	public void setTransRotHis_rotCenter(int transRotHis_rotCenter) {
		this.transRotHis_rotCenter = transRotHis_rotCenter;
	}

	public Point3d getTransRotHis_finalPos() {
		return transRotHis_finalPos;
	}

	public void setTransRotHis_finalPos(Point3d transRotHis_finalPos) {
		this.transRotHis_finalPos = transRotHis_finalPos;
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

	private Vector3d getCurvatureNormal() {
		return curvatureNormal;
	}

	private void setCurvatureNormal(Vector3d curvatureNormal) {
		this.curvatureNormal = curvatureNormal;
	}
}