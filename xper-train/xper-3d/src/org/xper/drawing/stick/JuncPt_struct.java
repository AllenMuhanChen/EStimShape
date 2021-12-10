package org.xper.drawing.stick;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 * Changed from a private class inside of org.xper.drawing.stick.MatchStick to public class
 * @author r2_allen
 *
 */
public class JuncPt_struct {
      public int nComp, nTangent;
      public int[] comp = new int[100];
      public int[] uNdx = new int[100];
      public Point3d pos = new Point3d();
      public Vector3d[] tangent = new Vector3d[100];
      public int[] tangentOwner = new int[100];
      public double rad;

      public JuncPt_struct()
      {
        int i;
        for (i=1; i<100; i++)
            tangent[i] = new Vector3d();
      }
      public JuncPt_struct(int in_nComp, int[] comp_list, int[] uNdx_list, Point3d in_pos, int in_nTangent, Vector3d[] tangent_list,
                int[] tangentOwner_list, double in_rad)
      {
        int i;
        nComp = in_nComp;
        nTangent = in_nTangent;
        for (i=1; i<=nComp; i++)
        {
            comp[i] = comp_list[i-1];
            uNdx[i] = uNdx_list[i-1];
        }
        pos.set( in_pos);
        // for convenice, create tangent vector entries totally
        for (i=1; i<100; i++)
            tangent[i] = new Vector3d();
        for (i=1; i<=nTangent; i++)
        {
            tangent[i].set(tangent_list[i-1]);
            tangentOwner[i] = tangentOwner_list[i-1];
        }
            rad = in_rad;
      }

      /**
        Copy any information from the structure in the paremeter
    */
      public void copyFrom( JuncPt_struct in)
      {
        int i;
        this.nComp = in.nComp;
        this.nTangent = in.nTangent;
        for (i=1; i<=nComp; i++)
        {
            comp[i] = in.comp[i];
            uNdx[i] = in.uNdx[i];
        }
        for (i=1; i<=nTangent; i++)
        {
            tangent[i] = new Vector3d( in.tangent[i]);
            tangentOwner[i] = in.tangentOwner[i];
        }
        pos.set( in.pos);
        rad = in.rad;
      }
      public void addComp(int newComp, int new_uNdx, Vector3d new_Tangent)
      {
    	  // As we know the new comp will always only bring in one new tangent vector
    	  nComp++;
    	  comp[nComp] = newComp;
    	  uNdx[nComp] = new_uNdx;
    	  nTangent++;
    	  tangent[nTangent].set( new_Tangent);
    	  tangentOwner[nTangent] = newComp;
      }

      public void removeComp(boolean[] removeList)
      {
        int i, j, k;
        for (j=1; j<= nComp; j++)
           if ( removeList[ comp[j] ] == true)
            {
//            System.out.println("at Junc:  the comp " + comp[j]  + " should be removed");
            // we just set the info to -1, the real clean will be done later
            comp[j] = -1;
            for (k=1; k<= nTangent; k++)
              if ( tangentOwner[k] == comp[j])
              {
                tangentOwner[k] = -1;
              }
            }

        // remove all the entries with -1 label
        int counter = 1;
        for (i=1; i<=nComp; i++)
           if (comp[i] != -1)
        {
            comp[counter] = comp[i];
            uNdx[counter] = uNdx[i];
            counter++;
        }
        nComp = counter -1;

        counter = 1;
        for (i=1; i<=nTangent; i++)
            if ( tangentOwner[i] != -1)
        {
            tangent[counter].set( tangent[i]);
            tangentOwner[counter] = tangentOwner[i];
            counter++;
        }
        nTangent = counter -1;

      }
      public void showInfo()
      {
     int i;
     System.out.println("nComp : " + nComp +" with rad: "+ rad);
     for ( i = 1; i<=nComp; i++)
          System.out.println(" comp " + comp[i]  + " with uNdx " + uNdx[i]);
//   System.out.println("Pos at : " + pos);
//   for ( i = 1 ; i<=nTangent; i++)
//        System.out.println(" tangent : " + tangent[i] + " belongs to " + tangentOwner[i]);
//   System.out.println("radius is " + rad +"\n----------------------------------\n\n");
      }
}
