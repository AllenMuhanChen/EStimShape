package org.xper.drawing.stick;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *  Class use to store JuncPt information
 */
public class JuncPt_Info
{
    public int nComp;
    public int nTangent;
    public Point3d pos;
    public double rad;
    public int[] comp;
    public int[] uNdx;
    public Vector3d[] tangent;
    public int[] tangentOwner;


    public void setJuncPtInfo(JuncPt_struct in_struct)
    {
        int i;
        this.nComp = in_struct.nComp;
        this.nTangent = in_struct.nTangent;
        this.pos = new Point3d( in_struct.pos);
        this.rad = in_struct.rad;

        comp = new int[nComp+1];
        uNdx = new int[nComp+1];
        tangent = new Vector3d[nTangent+1];
        tangentOwner = new int[nTangent+1];

        for (i=1; i<=nComp ;i++)
        {
            comp[i] = in_struct.comp[i];
            uNdx[i] = in_struct.uNdx[i];
        }
        for (i=1; i<=nTangent; i++)
        {
            tangent[i] = new Vector3d( in_struct.tangent[i]);
            tangentOwner[i] = in_struct.tangentOwner[i];
        }
    }
}
