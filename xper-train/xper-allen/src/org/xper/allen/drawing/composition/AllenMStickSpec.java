package org.xper.allen.drawing.composition;

import java.io.BufferedWriter;
import java.io.ByteArrayInputStream;
import java.io.DataInputStream;
import java.io.FileWriter;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.stick.EndPt_Info;
import org.xper.drawing.stick.JuncPt_Info;
import org.xper.drawing.stick.VertexInfo;

import com.thoughtworks.xstream.XStream;


public class AllenMStickSpec {
    private AllenMAxisInfo mAxis = new AllenMAxisInfo();
    public VertexInfo vertex = new VertexInfo();
    public boolean animation;
    public String compPosTanStr = "";
    RFStrategy rfStrategy;

    transient static XStream s;

    static {
        s = new XStream();
        s.alias("AllenMStickSpec", AllenMStickSpec.class);
        s.alias("EndPtInfo", EndPt_Info.class);
        s.alias("JuncPtInfo", JuncPt_Info.class);
        s.alias("AllenTubeInfo", AllenTubeInfo.class);

    }

    public void setMStickInfo(AllenMatchStick inStick, boolean saveVertexInfo)
    {
        getmAxis().setAllenMAxisInfo(inStick);

//		setSpecialEnd(inStick.getSpecialEnd());
//		setSpecialEndComp(inStick.getSpecialEndComp());
        if (saveVertexInfo)
            try {
                vertex.setVertexInfo(inStick.getSmoothObj());
            } catch (Exception e) {
                e.printStackTrace();
                throw new RuntimeException("Could not set vertex info");
            }


        AllenTubeComp[] tubes = inStick.getComp();

        compPosTanStr = "";
        for (int i=1; i<=getNComponent(); i++) {
            AllenMAxisArc tempArc = tubes[i].getmAxisInfo();
            compPosTanStr = compPosTanStr + i + "," + i + "," + i + "," +
                    tempArc.getCurvature() + "," + tempArc.getArcLen() + "," + tempArc.getRad() + "\n";
            for (int j=1; j<=51; j++) {
                compPosTanStr = compPosTanStr + tempArc.getmPts()[j].x + "," + tempArc.getmPts()[j].y + "," +
                        tempArc.getmPts()[j].z + "," + tempArc.getmTangent()[j].x + "," +
                        tempArc.getmTangent()[j].y + "," + tempArc.getmTangent()[j].z + "\n";
            }
        }

        this.rfStrategy = inStick.getRfStrategy();
    }

    /**
     *   Write the Match Stick information into a file
     */
    public void writeInfo2File(String fname) {

    		String faceStr = facToStr(getFacInfo(), getNFac());
        try {
        		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_face.txt"));

            out.write(faceStr);
            out.flush();
            out.close();
        } catch (Exception e) {
        		System.out.println(e);
        }

//        DbUtil dbu = new DbUtil();
//        dbu.writeFaceSpec(id, faceStr);

        String vertStr = vectToStr(getVectInfo(),getNVect());
        try {
        		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_vert.txt"));

            out.write(vertStr);
            out.flush();
            out.close();
        } catch (Exception e) {
        		System.out.println(e);
    		}

//        dbu.writeVertSpec(id, vertStr);

        String normStr = normToStr(getNormMatInfo(),getNVect());
        try {
        		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_norm.txt"));

            out.write(normStr);
            out.flush();
            out.close();
        } catch (Exception e) {
        		System.out.println(e);
    		}

        this.vertex = null;
        String specStr = this.toXml();
        try {
        		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_spec.xml"));

            out.write(specStr);
            out.flush();
            out.close();
        } catch (Exception e) {
        		System.out.println(e);
        }

        String outStr = compPosTanStr;
        try {
            BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_comp.txt"));
            out.write(  outStr);
            out.flush();
            out.close();
        } catch (Exception e) {
            System.out.println(e);
        }
    }


    public void writeInfo2File(String fname, boolean vertBool) {

    	if (vertBool) {
			String faceStr = facToStr(getFacInfo(), getNFac());
		    try {
	    		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_face.txt"));

		        out.write(faceStr);
		        out.flush();
		        out.close();
		    } catch (Exception e) {
	    		System.out.println(e);
		    }

		//    DbUtil dbu = new DbUtil();
		//    dbu.writeFaceSpec(id, faceStr);

		    String vertStr = vectToStr(getVectInfo(),getNVect());
		    try {
	    		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_vert.txt"));

		        out.write(vertStr);
		        out.flush();
		        out.close();
		    } catch (Exception e) {
	    		System.out.println(e);
			}

		//    dbu.writeVertSpec(id, vertStr);

		    String normStr = normToStr(getNormMatInfo(),getNVect());
		    try {
	    		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_norm.txt"));

		        out.write(normStr);
		        out.flush();
		        out.close();
		    } catch (Exception e) {
	    		System.out.println(e);
			}

            String outStr = compPosTanStr;
            try {
                BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_comp.txt"));
                out.write(  outStr);
                out.flush();
                out.close();
            } catch (Exception e) {
                System.out.println(e);
            }
    	}

	    this.vertex = null;
	    String specStr = toXml();
	    try {
    		BufferedWriter out = new BufferedWriter(new FileWriter(fname + "_spec.xml"));
	        out.write(specStr);
	        out.flush();
	        out.close();
	    } catch (Exception e) {
    		System.out.println(e);
	    }
    }

    public String toXml () {
        this.vertex = null;
        return AllenMStickSpec.toXml(this);
    }

    public static String toXml (AllenMStickSpec spec) {
        return s.toXML(spec);
    }

    public static AllenMStickSpec fromXml (String xml) {
        AllenMStickSpec g = (AllenMStickSpec)s.fromXML(xml);
        return g;
    }


    public boolean isAnimation() {
        return animation;
    }

    public void setAnimation(boolean animation) {
        this.animation = animation;
    }



    public Point3d[] getVectInfo()
    {
        int nVect = this.vertex.getnVect();
        int i;
        Point3d[] vect = new Point3d[ nVect+1];
        ByteArrayInputStream bis1 = new ByteArrayInputStream (vertex.vect_bArray);
        DataInputStream dis1 = new DataInputStream (bis1);
        try{

            double tx, ty, tz;
            for (i=1; i<=nVect; i++)
            {
                tx = dis1.readDouble(); ty = dis1.readDouble(); tz = dis1.readDouble();
                vect[i] = new Point3d( tx, ty, tz);
            }
        }
        catch (Exception e)
        { System.out.println(e);}

        return vect;
    }

    public Vector3d[] getNormMatInfo() {
        int nVect = this.vertex.getnVect();
        Vector3d[] normMat = new Vector3d[ nVect+1];
        ByteArrayInputStream bis2 = new ByteArrayInputStream (vertex.normMat_bArray);
        DataInputStream dis2 = new DataInputStream (bis2);
        int i;
        try{

            double tx, ty, tz;
            for (i=1; i<=nVect; i++)
            {
                tx = dis2.readDouble(); ty = dis2.readDouble(); tz = dis2.readDouble();
                normMat[i] = new Vector3d( tx, ty, tz);
            }

        }
        catch (Exception e)
        { System.out.println(e);}

        return normMat;
    }

    public int[][] getFacInfo() {
        // TODO Auto-generated method stub
        ByteArrayInputStream bis3 = new ByteArrayInputStream (vertex.fac_bArray);
        DataInputStream dis3 = new DataInputStream (bis3);
        int nFac = this.vertex.getnFac();
        int[][] facInfo =new int[ nFac][3];
        int i, j;

        try{
            for (i=0; i< nFac; i++)
                for (j=0; j<3; j++)
                    facInfo[i][j] = dis3.readInt();
        }
        catch (Exception e)
        { System.out.println(e);}

        return facInfo;
    }

	private String vectToStr(Point3d[] vect, int nVect) {
		String str = new String();

		for(int i=1; i<=nVect; i++) {
			str = str + vect[i].x + "," + vect[i].y + "," + vect[i].z + "\n";
		}
		return str;
	}

	private String facToStr(int[][] fac, int nFace) {
		String str = new String();
		for(int i=0; i<nFace; i++) {
			str = str + fac[i][0] + "," + fac[i][1] + "," + fac[i][2] + "\n";
		}
		return str;
	}

	private String normToStr(Vector3d[] vect, int nVect) {
		String str = new String();

		for(int i=1; i<=nVect; i++) {
			str = str + vect[i].x + "," + vect[i].y + "," + vect[i].z + "\n";
		}
		return str;
	}


    public int getNFac() {
        // TODO Auto-generated method stub
        return this.vertex.getnFac();
    }
    public int getNVect(){
        return this.vertex.getnVect();
    }

    public int getNComponent(){
        return this.getmAxis().getnComponent();
    }

	public AllenMAxisInfo getmAxis() {
		return mAxis;
	}

	public void setmAxis(AllenMAxisInfo mAxis) {
		this.mAxis = mAxis;
	}

    @Override
    public String toString() {
        return "AllenMStickSpec{" +
                "mAxis=" + mAxis +
                ", vertex=" + vertex +
                ", animation=" + animation +
                ", compPosTanStr='" + compPosTanStr + '\'' +
                '}';
    }

    public RFStrategy getRfStrategy() {
        return rfStrategy;
    }

    public void setRfStrategy(RFStrategy rfStrategy) {
        this.rfStrategy = rfStrategy;
    }
}