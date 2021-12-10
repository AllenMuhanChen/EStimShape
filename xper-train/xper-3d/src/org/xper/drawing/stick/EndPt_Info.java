package org.xper.drawing.stick;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *
 * class use to store EndPt information
 */
public class EndPt_Info
{
    public int comp;
    public int uNdx;
    public Point3d pos;
    public Vector3d tangent;
    public double rad;

    public void setEndPtInfo( EndPt_struct in_struct)
    {
        this.comp = in_struct.comp;
        this.uNdx = in_struct.uNdx;
        this.pos = new Point3d( in_struct.pos);
        this.tangent = new Vector3d( in_struct.tangent);
        this.rad = in_struct.rad;

    }
}