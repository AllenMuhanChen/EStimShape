package org.xper.drawing.stick;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 * Changed from a private class inside of org.xper.drawing.stick.MatchStick to public class
 * @author r2_allen
 *
 */
public class JuncPt_struct {
      private int nComp;
	private int nTangent;
      private int[] comp = new int[100];
      private int[] uNdx = new int[100];
      private Point3d pos = new Point3d();
      private Vector3d[] tangent = new Vector3d[100];
      private int[] tangentOwner = new int[100];
      private double rad;

      public JuncPt_struct()
      {
        int i;
        for (i=1; i<100; i++)
            getTangent()[i] = new Vector3d();
      }
      public JuncPt_struct(int in_nComp, int[] comp_list, int[] uNdx_list, Point3d in_pos, int in_nTangent, Vector3d[] tangent_list,
                int[] tangentOwner_list, double in_rad)
      {
        int i;
        setnComp(in_nComp);
        setnTangent(in_nTangent);
        for (i=1; i<=getnComp(); i++)
        {
            getCompIds()[i] = comp_list[i-1];
            getuNdx()[i] = uNdx_list[i-1];
        }
        getPos().set( in_pos);
        // for convenice, create tangent vector entries totally
        for (i=1; i<100; i++)
            getTangent()[i] = new Vector3d();
        for (i=1; i<=getnTangent(); i++)
        {
            getTangent()[i].set(tangent_list[i-1]);
            getTangentOwner()[i] = tangentOwner_list[i-1];
        }
            setRad(in_rad);
      }

      /**
       * AC:
       * Return the index in comp[100] associated with a certain comp
       * @return
       */
      public int getJIndexOfComp(int compId) {
    	  for(int JIndx=1; JIndx<comp.length; JIndx++) {
    		  if(comp[JIndx]==compId) {
    			  return JIndx;
    		  }
    	  }
//    	  System.out.println("getIndexOfComp(int compId) returned 0, this should means that compId is not a component in this Junc");
    	  return 0;
      }

    public Vector3d getTangentOfOwner(int ownerCompId){
        for (int tanIndx=1; tanIndx<= getnTangent(); tanIndx++)
            if ( getTangentOwner()[tanIndx] == getCompIds()[ownerCompId])
            {
                return getTangent()[tanIndx];
            }
          return null;
      }

      /**
        Copy any information from the structure in the paremeter
    */
      public void copyFrom( JuncPt_struct in)
      {
        int i;
        this.setnComp(in.getnComp());
        this.setnTangent(in.getnTangent());
        for (i=1; i<=getnComp(); i++)
        {
            getCompIds()[i] = in.getCompIds()[i];
            getuNdx()[i] = in.getuNdx()[i];
        }
        for (i=1; i<=getnTangent(); i++)
        {
            getTangent()[i] = new Vector3d( in.getTangent()[i]);
            getTangentOwner()[i] = in.getTangentOwner()[i];
        }
        getPos().set( in.getPos());
        setRad(in.getRad());
      }
      public void addComp(int newComp, int new_uNdx, Vector3d new_Tangent)
      {
    	  // As we know the new comp will always only bring in one new tangent vector
    	  setnComp(getnComp() + 1);
    	  getCompIds()[getnComp()] = newComp;
    	  getuNdx()[getnComp()] = new_uNdx;
    	  setnTangent(getnTangent() + 1);
    	  getTangent()[getnTangent()].set( new_Tangent);
    	  getTangentOwner()[getnTangent()] = newComp;
      }

      public void removeComp(boolean[] removeList)
      {
        int i, j, k;
        for (j=1; j<= getnComp(); j++)
           if ( removeList[ getCompIds()[j] ] == true)
            {
//            System.out.println("at Junc:  the comp " + comp[j]  + " should be removed");
            // we just set the info to -1, the real clean will be done later
            getCompIds()[j] = -1;
            for (k=1; k<= getnTangent(); k++)
              if ( getTangentOwner()[k] == getCompIds()[j])
              {
                getTangentOwner()[k] = -1;
              }
            }

        // remove all the entries with -1 label
        int counter = 1;
        for (i=1; i<=getnComp(); i++)
           if (getCompIds()[i] != -1)
        {
            getCompIds()[counter] = getCompIds()[i];
            getuNdx()[counter] = getuNdx()[i];
            counter++;
        }
        setnComp(counter -1);

        counter = 1;
        for (i=1; i<=getnTangent(); i++)
            if ( getTangentOwner()[i] != -1)
        {
            getTangent()[counter].set( getTangent()[i]);
            getTangentOwner()[counter] = getTangentOwner()[i];
            counter++;
        }
        setnTangent(counter -1);

      }
      public void showInfo()
      {
     int i;
     System.out.println("nComp : " + getnComp() +" with rad: "+ getRad());
     for ( i = 1; i<=getnComp(); i++)
          System.out.println(" comp " + getCompIds()[i]  + " with uNdx " + getuNdx()[i]);
//   System.out.println("Pos at : " + pos);
//   for ( i = 1 ; i<=nTangent; i++)
//        System.out.println(" tangent : " + tangent[i] + " belongs to " + tangentOwner[i]);
//   System.out.println("radius is " + rad +"\n----------------------------------\n\n");
      }
	public int[] getCompIds() {
		return comp;
	}
	public void setComp(int[] comp) {
		this.comp = comp;
	}
	public int getnComp() {
		return nComp;
	}
	public void setnComp(int nComp) {
		this.nComp = nComp;
	}
	public int getnTangent() {
		return nTangent;
	}
	public void setnTangent(int nTangent) {
		this.nTangent = nTangent;
	}
	public int[] getuNdx() {
		return uNdx;
	}
	public void setuNdx(int[] uNdx) {
		this.uNdx = uNdx;
	}
	public Point3d getPos() {
		return pos;
	}
	public void setPos(Point3d pos) {
		this.pos = pos;
	}
	public Vector3d[] getTangent() {
		return tangent;
	}
	public void setTangent(Vector3d[] tangent) {
		this.tangent = tangent;
	}
	public int[] getTangentOwner() {
		return tangentOwner;
	}
	public void setTangentOwner(int[] tangentOwner) {
		this.tangentOwner = tangentOwner;
	}
	public double getRad() {
		return rad;
	}
	public void setRad(double rad) {
		this.rad = rad;
	}
}