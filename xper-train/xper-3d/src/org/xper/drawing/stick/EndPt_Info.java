package org.xper.drawing.stick;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *
 * class use to store EndPt information
 */
public class EndPt_Info
{
    private int comp;
    private int uNdx;
    private Point3d pos;
    private Vector3d tangent;
    private double rad;

    public void setEndPtInfo( EndPt_struct in_struct)
    {
        this.setComp(in_struct.getComp());
        this.setuNdx(in_struct.getuNdx());
        this.setPos(new Point3d( in_struct.getPos()));
        this.setTangent(new Vector3d( in_struct.getTangent()));
        this.setRad(in_struct.getRad());

    }

	public int getComp() {
		return comp;
	}

	public void setComp(int comp) {
		this.comp = comp;
	}

	public int getuNdx() {
		return uNdx;
	}

	public void setuNdx(int uNdx) {
		this.uNdx = uNdx;
	}

	public Point3d getPos() {
		return pos;
	}

	public void setPos(Point3d pos) {
		this.pos = pos;
	}

	public Vector3d getTangent() {
		return tangent;
	}

	public void setTangent(Vector3d tangent) {
		this.tangent = tangent;
	}

	public double getRad() {
		return rad;
	}

	public void setRad(double rad) {
		this.rad = rad;
	}
}