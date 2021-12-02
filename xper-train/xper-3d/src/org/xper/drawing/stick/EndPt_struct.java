package org.xper.drawing.stick;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
/**
 * Changed from a private class inside of org.xper.drawing.stick.MatchStick to public class
 * @author r2_allen
 *
 */
public class EndPt_struct {
      public int comp, uNdx; // identify which component's which uNdx contribute to this endPt
      public Point3d pos = new Point3d();
      public Vector3d tangent = new Vector3d();
      public double rad; // the radius value at this point
      public EndPt_struct()
    {
    }
      public EndPt_struct(int in_comp, int in_uNdx, Point3d in_pos, Vector3d in_tangent, double in_rad)
      {
      comp = in_comp; uNdx = in_uNdx;
      pos.set( in_pos);
          tangent.set( in_tangent);
      rad = in_rad;
      if (in_uNdx == 51) // the last end
          tangent.negate(); // reverse the direction of tangent

      }

      public void copyFrom(EndPt_struct in)
      {

        this.comp = in.comp;
        this.uNdx = in.uNdx;
        this.tangent.set(in.tangent);
        this.pos.set( in.pos);
        this.rad = in.rad;

      }

      public void setValue(int in_comp, int in_uNdx, Point3d in_pos, Vector3d in_tangent, double in_rad)
      {
      comp = in_comp; uNdx = in_uNdx;
      pos.set( in_pos);
      tangent.set( in_tangent);
      rad = in_rad;
      if (in_uNdx == 51) // the last end
          tangent.negate(); // reverse the direction of tangent
      }
      public void showInfo()
      {
        System.out.println("endPt with comp "+ comp + " uNdx: "+ uNdx +" with rad: "+ rad);
      }
      public String toString()
      {
      return "End Pt Info: (comp,uNdx) = " + comp +" , " +uNdx + "\n  pos = " + pos + "\n  tangent = " + tangent + "  rad = " + rad;
      }
}
