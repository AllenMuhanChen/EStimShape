package org.xper.drawing.stick;

import java.io.BufferedWriter;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.FileWriter;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import com.thoughtworks.xstream.XStream;

/**
 * @author aldenhung
 *
 */

/**
 *  Class use to store JuncPt information
 */
class JuncPt_Info
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

/**
 *
 * class use to store EndPt information
 */
class EndPt_Info
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
/**
 *   class that store the information about a single tube
 *   The info include the MAxis and also the radius quadratic function.
 */
class TubeInfo
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
/*
class MAxisInfo
{
    public int nComponent;
    public int nEndPt;
    public int nJuncPt;
    public double[] finalRotation = new double[3];
    //public JuncPt_Info[] JuncPt;
    public EndPt_Info[] EndPt;
    public JuncPt_Info[] JuncPt;
    public TubeInfo[] Tube;
    //private TubeComp[] comp = new TubeComp[9];
    //private EndPt_struct[] endPt = new EndPt_struct[30]; // 30 is just an arbitrary large enough number
    //private JuncPt_struct[] JuncPt = new JuncPt_struct[30];
    //private MStickObj4Smooth obj1;
    public void setMAxisInfo(MatchStick inStick)
    {
        int i;
        this.nComponent = inStick.nComponent;
        this.nEndPt = inStick.nEndPt;
        this.nJuncPt = inStick.nJuncPt;

        this.JuncPt = new JuncPt_Info[nJuncPt+1];
        this.EndPt  = new EndPt_Info[nEndPt+1];
        this.Tube = new TubeInfo[nComponent+1];
        for (i=1; i<= nEndPt; i++)
        {
            EndPt[i] = new EndPt_Info();
            EndPt[i].setEndPtInfo( inStick.endPt[i]);

        }
        for (i=1; i<= nJuncPt; i++)
        {
            JuncPt[i] = new JuncPt_Info();
            JuncPt[i].setJuncPtInfo( inStick.JuncPt[i]);
        }

        for (i=1; i<= nComponent; i++)
        {
            Tube[i] = new TubeInfo();
            Tube[i].setTubeInfo(inStick.comp[i]);
        }

        for (i=0; i<3; i++)
            finalRotation[i] = inStick.finalRotation[i];

    }

}
*/
/**
 *  This class store the vertex and face information for fast rendering
 *
 */
class VertexInfo
{
    public int nVect;
    public int nFac;
    //transient public Point3d[] vect;
    //transient public Vector3d[] normMat;
    //transient public int[][] facInfo;

    public byte[] vect_bArray;
    public byte[] normMat_bArray;
    public byte[] fac_bArray;
    public void showDebug()
    {
        Point3d[] vect = new Point3d[ nVect+1];
        Vector3d[] normMat = new Vector3d[ nVect+1];
        int[][] facInfo =new int[ nFac][3];
        int i, j;
        // now we implement read the vect, normMat, fac Info out of the byte array
        ByteArrayInputStream bis1 = new ByteArrayInputStream (vect_bArray);
        DataInputStream dis1 = new DataInputStream (bis1);

        ByteArrayInputStream bis2 = new ByteArrayInputStream (normMat_bArray);
        DataInputStream dis2 = new DataInputStream (bis2);

        ByteArrayInputStream bis3 = new ByteArrayInputStream (fac_bArray);
        DataInputStream dis3 = new DataInputStream (bis3);

        try{

            double tx, ty, tz;
            for (i=1; i<=nVect; i++)
            {
                tx = dis1.readDouble(); ty = dis1.readDouble(); tz = dis1.readDouble();
                vect[i] = new Point3d( tx, ty, tz);

                tx = dis2.readDouble(); ty = dis2.readDouble(); tz = dis2.readDouble();
                normMat[i] = new Vector3d( tx, ty, tz);
            }
            for (i=0; i< nFac; i++)
                for (j=0; j<3; j++)
                    facInfo[i][j] = dis3.readInt();
        }
        catch (Exception e)
        { System.out.println(e);}

        //debug
        System.out.println("vect 3 info_ decoded");
        System.out.println(vect[71]);
        System.out.println(normMat[193]);
        System.out.println(facInfo[3][0]);
        System.out.println(facInfo[3][1]);
        System.out.println(facInfo[3][2]);
    }
    public void setVertexInfo(MStickObj4Smooth inObj)
    {
        int i, j;
        this.nVect = inObj.nVect;
        this.nFac = inObj.nFac;

        int buf_size = nVect * 3 * 8; // 8 is the size of double
        ByteArrayOutputStream bos1 = new java.io.ByteArrayOutputStream(buf_size);
        DataOutputStream dos1 = new DataOutputStream(bos1);

        ByteArrayOutputStream bos2 = new java.io.ByteArrayOutputStream(buf_size);
        DataOutputStream dos2 = new DataOutputStream(bos2);

        buf_size = nFac * 4 * 3; // 4 is the size of int
        ByteArrayOutputStream bos3 = new java.io.ByteArrayOutputStream(buf_size);
        DataOutputStream dos3 = new DataOutputStream(bos3);
        // note: dos1 for vect_info, dos2 for normMat
        // dos3 for fac Info
      try{
            for (i=1; i<=nVect; i++)
            {
                dos1.writeDouble( inObj.vect_info[i].x);
                dos1.writeDouble( inObj.vect_info[i].y);
                dos1.writeDouble( inObj.vect_info[i].z);
                dos2.writeDouble( inObj.normMat_info[i].x);
                dos2.writeDouble( inObj.normMat_info[i].y);
                dos2.writeDouble( inObj.normMat_info[i].z);

            }
            dos1.flush();
            dos2.flush();

            vect_bArray= bos1.toByteArray();
            normMat_bArray = bos2.toByteArray();

            for (i=0; i<nFac; i++)
                for (j=0; j<3; j++)
                {
                    dos3.writeInt( inObj.facInfo[i][j]);
                }
            dos3.flush();
            fac_bArray = bos3.toByteArray();
        }
        catch(Exception e)
          { System.out.println(e);}
    }

}


public class MStickSpec {
    public MAxisInfo mAxis = new MAxisInfo();
    public VertexInfo vertex = new VertexInfo();
    public boolean animation;
    public String compPosTanStr = "";

    transient static XStream s;

    static {
        s = new XStream();
        s.alias("MStickSpec", MStickSpec.class);
        s.alias("EndPtInfo", EndPt_Info.class);
        s.alias("JuncPtInfo", JuncPt_Info.class);
        s.alias("TubeInfo", TubeInfo.class);
        
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
	    String specStr = this.toXml();
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
        return MStickSpec.toXml(this);
    }

    public static String toXml (MStickSpec spec) {
        return s.toXML(spec);
    }

    public static MStickSpec fromXml (String xml) {
        MStickSpec g = (MStickSpec)s.fromXML(xml);
        return g;
    }


    public boolean isAnimation() {
        return animation;
    }

    public void setAnimation(boolean animation) {
        this.animation = animation;
    }

    public void setMStickInfo( MatchStick inStick)
    {
		this.mAxis.setMAxisInfo(inStick);
		this.vertex.setVertexInfo(inStick.getSmoothObj());

        TubeComp[] tubes = inStick.getComp();
        
        compPosTanStr = "";
        for (int i=1; i<=getNComponent(); i++) {
            MAxisArc tempArc = tubes[i].mAxisInfo;
            compPosTanStr = compPosTanStr + i + "," + i + "," + i + "," + 
                    tempArc.curvature + "," + tempArc.arcLen + "," + tempArc.rad + "\n";
            for (int j=1; j<=51; j++) {
                compPosTanStr = compPosTanStr + tempArc.mPts[j].x + "," + tempArc.mPts[j].y + "," + 
                        tempArc.mPts[j].z + "," + tempArc.mTangent[j].x + "," + 
                        tempArc.mTangent[j].y + "," + tempArc.mTangent[j].z + "\n";
                
                
            }
        }
    }



    public Point3d[] getVectInfo()
    {
        int nVect = this.vertex.nVect;
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
        int nVect = this.vertex.nVect;
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
        int nFac = this.vertex.nFac;
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
        return this.vertex.nFac;
    }
    public int getNVect(){
        return this.vertex.nVect;
    }

    public int getNComponent(){
        return this.mAxis.nComponent;
    }






}
