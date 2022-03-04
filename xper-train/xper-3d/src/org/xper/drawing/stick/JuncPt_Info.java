package org.xper.drawing.stick;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *  Class use to store JuncPt information
 */
public class JuncPt_Info
{
    private int nComp;
    private int nTangent;
    private Point3d pos;
    private double rad;
    private int[] comp;
    private int[] uNdx;
    private Vector3d[] tangent;
    private int[] tangentOwner;


    public void setJuncPtInfo(JuncPt_struct in_struct)
    {
        int i;
        this.setnComp(in_struct.getnComp());
        this.setnTangent(in_struct.getnTangent());
        this.setPos(new Point3d( in_struct.getPos()));
        this.setRad(in_struct.getRad());

        setComp(new int[getnComp()+1]);
        setuNdx(new int[getnComp()+1]);
        setTangent(new Vector3d[getnTangent()+1]);
        setTangentOwner(new int[getnTangent()+1]);

        for (i=1; i<=getnComp() ;i++)
        {
            getComp()[i] = in_struct.getComp()[i];
            getuNdx()[i] = in_struct.getuNdx()[i];
        }
        for (i=1; i<=getnTangent(); i++)
        {
            getTangent()[i] = new Vector3d( in_struct.getTangent()[i]);
            getTangentOwner()[i] = in_struct.getTangentOwner()[i];
        }
    }


	public int[] getuNdx() {
		return uNdx;
	}


	public void setuNdx(int[] uNdx) {
		this.uNdx = uNdx;
	}


	public int[] getComp() {
		return comp;
	}


	public void setComp(int[] comp) {
		this.comp = comp;
	}


	public Point3d getPos() {
		return pos;
	}


	public void setPos(Point3d pos) {
		this.pos = pos;
	}


	public double getRad() {
		return rad;
	}


	public void setRad(double rad) {
		this.rad = rad;
	}


	public int getnTangent() {
		return nTangent;
	}


	public void setnTangent(int nTangent) {
		this.nTangent = nTangent;
	}


	public int getnComp() {
		return nComp;
	}


	public void setnComp(int nComp) {
		this.nComp = nComp;
	}


	public int[] getTangentOwner() {
		return tangentOwner;
	}


	public void setTangentOwner(int[] tangentOwner) {
		this.tangentOwner = tangentOwner;
	}


	public Vector3d[] getTangent() {
		return tangent;
	}


	public void setTangent(Vector3d[] tangent) {
		this.tangent = tangent;
	}
}
