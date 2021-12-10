package org.xper.drawing.stick;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *   class that store the information about a single tube
 *   The info include the MAxis and also the radius quadratic function.
 */
public class TubeInfo
{


    public boolean branchUsed;
    public int connectType;
    public double[][] radInfo = new double[3][2];

    public double mAxis_rad;
    public double mAxis_arcLen; // only these two are important
                                //curvature & angleExtend can be calculated
    public int mAxis_branchPt;

    public int transRotHis_alignedPt;
    public int transRotHis_rotCenter;
    public Point3d transRotHis_finalPos;
    public Vector3d transRotHis_finalTangent;
    public double transRotHis_devAngle;

    public void setTubeInfo(TubeComp inTube)
    {
        int i, j;
        this.branchUsed = inTube.branchUsed;
        this.connectType = inTube.connectType;
        for (i=0; i<3; i++)
            for (j=0; j<2; j++)
                this.radInfo[i][j] = inTube.radInfo[i][j];

        //mAxis related
        this.mAxis_arcLen = inTube.mAxisInfo.arcLen;
        this.mAxis_rad = inTube.mAxisInfo.rad;
        this.mAxis_branchPt = inTube.mAxisInfo.branchPt;

        //mAxis transRotHis related
        this.transRotHis_alignedPt = inTube.mAxisInfo.transRotHis_alignedPt;
        this.transRotHis_rotCenter = inTube.mAxisInfo.transRotHis_rotCenter;
        this.transRotHis_finalPos
                        = new Point3d(inTube.mAxisInfo.transRotHis_finalPos);
        this.transRotHis_finalTangent
                       = new Vector3d(inTube.mAxisInfo.transRotHis_finalTangent);
        this.transRotHis_devAngle = inTube.mAxisInfo.transRotHis_devAngle;

    }
}