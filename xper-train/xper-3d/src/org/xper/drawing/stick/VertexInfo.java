package org.xper.drawing.stick;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

/**
 *  This class store the vertex and face information for fast rendering
 *
 */
public class VertexInfo
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
