package org.xper.drawing.stick;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
/**
 * Changed from a private class inside of org.xper.drawing.stick.MatchStick to public class
 * @author r2_allen
 *
 */
public class EndPt_struct {
      private int comp; // identify which component's which uNdx contribute to this endPt
	private int uNdx;
      private Point3d pos = new Point3d();
      private Vector3d tangent = new Vector3d();
      private double rad; // the radius value at this point
      public EndPt_struct()
    {
    }
      public EndPt_struct(int in_comp, int in_uNdx, Point3d in_pos, Vector3d in_tangent, double in_rad)
      {
      setComp(in_comp); setuNdx(in_uNdx);
      getPos().set( in_pos);
          getTangent().set( in_tangent);
      setRad(in_rad);
      if (in_uNdx == 51) // the last end
          getTangent().negate(); // reverse the direction of tangent

      }

      public void copyFrom(EndPt_struct in)
      {

        this.setComp(in.getComp());
        this.setuNdx(in.getuNdx());
        this.getTangent().set(in.getTangent());
        this.getPos().set( in.getPos());
        this.setRad(in.getRad());

      }

      public void setValue(int in_comp, int in_uNdx, Point3d in_pos, Vector3d in_tangent, double in_rad)
      {
      setComp(in_comp); setuNdx(in_uNdx);
      getPos().set( in_pos);
      getTangent().set( in_tangent);
      setRad(in_rad);
      if (in_uNdx == 51) // the last end
          getTangent().negate(); // reverse the direction of tangent
      }
      public void showInfo()
      {
        System.out.println("endPt with comp "+ getComp() + " uNdx: "+ getuNdx() +" with rad: "+ getRad());
      }
      public String toString()
      {
      return "End Pt Info: (comp,uNdx) = " + getComp() +" , " +getuNdx() + "\n  pos = " + getPos() + "\n  tangent = " + getTangent() + "  rad = " + getRad();
      }
	public int getComp() {
		return comp;
	}
	public void setComp(int comp) {
		this.comp = comp;
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
	public int getuNdx() {
		return uNdx;
	}
	public void setuNdx(int uNdx) {
		this.uNdx = uNdx;
	}
	public double getRad() {
		return rad;
	}
	public void setRad(double rad) {
		this.rad = rad;
	}
}
