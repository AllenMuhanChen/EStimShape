package org.xper.drawing.stick;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.lwjgl.opengl.GL11;
import org.xper.utils.RGBColor;

public class MStickObj4Smooth {
    public int nComponent;
    public int[] vect_type = new int[25000];
    public int[] vectTag = new int[25000];
    public int nIntersectPatch = 0;
    public TubeComp[] comp;
    private static final int MAX_COMP = 11;

    private Point3d maxXYZ;
    private Point3d minXYZ;

    public Point3d[] vect_info = new Point3d[25000]; // not sure if 15000 will work..let's see
    public Vector3d[] normMat_info = new Vector3d[25000];
    private int[][] facInfo = new int[45000][3];
    private int nVect;
    private int nFac;

    public boolean doLighting = false;
    public double contrast = 0.5;
    public RGBColor stimColor = new RGBColor(1,1,1);

    /**
     * AC: Deep copy constructor
     * @param original
     */
    public MStickObj4Smooth(MStickObj4Smooth original) {
        this.nComponent = original.nComponent;
        this.nIntersectPatch = original.nIntersectPatch;
        this.nVect = original.nVect;
        this.nFac = original.nFac;
        this.doLighting = original.doLighting;
        this.contrast = original.contrast;
        this.stimColor = new RGBColor(original.stimColor.getRed(), original.stimColor.getGreen(), original.stimColor.getBlue());

        this.maxXYZ = new Point3d(original.maxXYZ);
        this.minXYZ = new Point3d(original.minXYZ);

        this.vect_type = new int[original.vect_type.length];
        System.arraycopy(original.vect_type, 0, this.vect_type, 0, original.vect_type.length);

        this.vectTag = new int[original.vectTag.length];
        System.arraycopy(original.vectTag, 0, this.vectTag, 0, original.vectTag.length);

        this.vect_info = new Point3d[original.vect_info.length];
        for (int i = 0; i < original.vect_info.length; i++) {
            if (original.vect_info[i] != null) {
                this.vect_info[i] = new Point3d(original.vect_info[i]);
            }
        }

        this.normMat_info = new Vector3d[original.normMat_info.length];
        for (int i = 0; i < original.normMat_info.length; i++) {
            if (original.normMat_info[i] != null) {
                this.normMat_info[i] = new Vector3d(original.normMat_info[i]);
            }
        }

        this.facInfo = new int[original.facInfo.length][3];
        for (int i = 0; i < original.facInfo.length; i++) {
            System.arraycopy(original.facInfo[i], 0, this.facInfo[i], 0, original.facInfo[i].length);
        }

        this.comp = new TubeComp[original.comp.length];
        for (int i = 1; i <= original.nComponent; i++) {
            if (original.comp[i] != null) {
                this.comp[i] = new TubeComp();
                this.comp[i].copyFrom(original.comp[i]);
            }
        }
    }



    public void setInfo(int inVect, Point3d[] ivect_info, Vector3d[] inormMat_info, int inFac, int[][] ifacInfo)
    {
        int i, j;
        //just copy the vect, fac info.
        this.setnVect(inVect);
        this.setnFac(inFac);

        for (i=1; i<= getnVect(); i++)
        {
            this.vect_info[i] = new Point3d( ivect_info[i]);
            this.normMat_info[i] = new Vector3d(inormMat_info[i]);
        }

        for (i=0; i< getnFac(); i++)
            for (j=0; j<3; j++)
            {
                getFacInfo()[i][j] = ifacInfo[i][j];
            }


    }

    /*
     *   This is going to translate the transVec
     *   The result is that the shape will be recentered at inside-the-shape
     */
    public void translateBack( Point3d transVec)
    {
        int i;
        for (i=1; i<= getnVect(); i++)
        {
            vect_info[i].x += transVec.x;
            vect_info[i].y += transVec.y;
            vect_info[i].z += transVec.z;
        }
    }

    public void translateFwd( Point3d transVec)
    {
        int i;
        for (i=1; i<= getnVect(); i++)
        {
            vect_info[i].x -= transVec.x;
            vect_info[i].y -= transVec.y;
            vect_info[i].z -= transVec.z;
        }
    }

    public void scaleTheObj(double scaleFactor)
    {
        int i;
        for (i=1; i<= getnVect(); i++)
        {
            vect_info[i].x *= scaleFactor;
            vect_info[i].y *= scaleFactor;
            vect_info[i].z *= scaleFactor;

        }
    }

    public void fake_objectMerge(MStickObj4Smooth inObj)
    {
        // two main roles here are this (1) & inObj (2)

        //merge the vect and fac info into one
        //MStickObj4Smooth obj1 = this;
        MStickObj4Smooth obj2 = inObj;
        int ori_nVect = this.getnVect();
        int ori_nFac = this.getnFac();
        this.setnVect(ori_nVect + obj2.getnVect());
        this.setnFac(ori_nFac    + obj2.getnFac());

        // put the vec & normMat info into this.vect
        int i, j;
        for (i=1; i<= obj2.getnVect(); i++)
        {

            this.vect_info[i+ ori_nVect] = new Point3d( obj2.vect_info[i]);
            //  System.out.println("now " + (i + ori_nVect));
            //System.out.println( this.vect_info[i+ori_nVect]);
            this.normMat_info[i+ori_nVect]
                    = new Vector3d( obj2.normMat_info[i]);
            this.vect_type[i] = 0;
        }

        for (i=0; i< obj2.getnFac(); i++)
            for (j=0; j<3; j++)
            {
                this.getFacInfo()[i + ori_nFac][j] = obj2.getFacInfo()[i][j] + ori_nVect;
            }

        //System.out.println("Now nVect, nFac" + nVect +" " + nFac);
        //for (i=1; i<= this.nVect; i++)
        // update AABB
        // seems not necessary
        /*
        if (inObj.minXYZ.x < this.minXYZ.x)  this.minXYZ.x =  inObj.minXYZ.x;
        if (inObj.minXYZ.y < this.minXYZ.y)  this.minXYZ.y =  inObj.minXYZ.y;
        if (inObj.minXYZ.z < this.minXYZ.z)  this.minXYZ.z =  inObj.minXYZ.z;

        if (inObj.maxXYZ.x > this.maxXYZ.x)  this.maxXYZ.x =  inObj.maxXYZ.x;
        if (inObj.maxXYZ.y > this.maxXYZ.y)  this.maxXYZ.y =  inObj.maxXYZ.y;
        if (inObj.maxXYZ.z > this.maxXYZ.z)  this.maxXYZ.z =  inObj.maxXYZ.z;
        */
    }


    public void rotateMesh( double[] rotVec)
    {
        int i;
        // 1. rot X
        if ( rotVec[0] != 0.0)
        {
            Vector3d RotAxis = new Vector3d(1,0,0);
            double Angle = (rotVec[0] /180.0 ) *Math.PI;
            AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
            Transform3D transMat = new Transform3D();
            transMat.setRotation(axisInfo);
            for (i=1; i<= getnVect(); i++)
            {
                //  System.out.println(i + " " + vect_info[i].x);
                transMat.transform( vect_info[i]);
                transMat.transform( normMat_info[i]);
            }
        }
        // 2. rot Y
        if ( rotVec[1] != 0.0)
        {
            Vector3d RotAxis = new Vector3d(0,1,0);
            double Angle = (rotVec[1] /180.0 ) *Math.PI;
            AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
            Transform3D transMat = new Transform3D();
            transMat.setRotation(axisInfo);
            for (i=1; i<= getnVect(); i++)
            {
                transMat.transform( vect_info[i]);
                transMat.transform( normMat_info[i]);
            }
        }

        // 3. rot Z
        if ( rotVec[2] != 0.0)
        {
            Vector3d RotAxis = new Vector3d(0,0,1);
            double Angle = (rotVec[2] /180.0 ) *Math.PI;
            AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
            Transform3D transMat = new Transform3D();
            transMat.setRotation(axisInfo);
            for (i=1; i<= getnVect(); i++)
            {
                transMat.transform( vect_info[i]);
                transMat.transform( normMat_info[i]);
            }
        }

    }
    public void drawVectTranslucent(float alpha) {
        if (isDoLighting())
            GL11.glEnable(GL11.GL_LIGHTING);
        else
            GL11.glDisable(GL11.GL_LIGHTING);

        for (int i = 0; i< getnFac(); i++) {
            GL11.glBegin(GL11.GL_TRIANGLES);

            GL11.glColor4d(getStimColor().getRed(), getStimColor().getGreen(), getStimColor().getBlue(), alpha);

            Point3d p1 = vect_info[ getFacInfo()[i][0]];
            Point3d p2 = vect_info[ getFacInfo()[i][1]];
            Point3d p3 = vect_info[ getFacInfo()[i][2]];
            Vector3d v1 = normMat_info[ getFacInfo()[i][0]];
            Vector3d v2 = normMat_info[ getFacInfo()[i][1]];
            Vector3d v3 = normMat_info[ getFacInfo()[i][2]];
            if ( v1.length() >= 1.01 || v1.length() <= 0.99) {
                System.out.println("error in v1 length as:");
                System.out.println(v1.x +" "+ v1.y + " " +v1.z);
                System.out.println(v1.length());
            }
            if ( v2.length() >= 1.01 || v2.length() <= 0.99) {
                System.out.println("error in v2 length as:");
                System.out.println(v2.x +" "+ v2.y + " " +v2.z);
                System.out.println(v2.length());
            }
            if ( v3.length() >= 1.01 || v3.length() <= 0.99) {
                System.out.println("error in v3 length as:");
                System.out.println(v3.x +" "+ v3.y + " " +v3.z);
                System.out.println(v3.length());
            }

            GL11.glNormal3d( v1.x, v1.y, v1.z);
            GL11.glVertex3d( p1.x, p1.y, p1.z);
            GL11.glNormal3d( v2.x, v2.y, v2.z);
            GL11.glVertex3d( p2.x, p2.y, p2.z);
            GL11.glNormal3d( v3.x, v3.y, v3.z);
            GL11.glVertex3d( p3.x, p3.y, p3.z);

            GL11.glEnd();
        }
        GL11.glDisable(GL11.GL_LIGHTING);
    }

    public void drawVect() {
        GL11.glColor3d(getStimColor().getRed(), getStimColor().getGreen(), getStimColor().getBlue());
        if (isDoLighting())
            GL11.glEnable(GL11.GL_LIGHTING);
        else
            GL11.glDisable(GL11.GL_LIGHTING);

        for (int i = 0; i< getnFac(); i++) {
            GL11.glBegin(GL11.GL_TRIANGLES);


            Point3d p1 = vect_info[ getFacInfo()[i][0]];
            Point3d p2 = vect_info[ getFacInfo()[i][1]];
            Point3d p3 = vect_info[ getFacInfo()[i][2]];
            Vector3d v1 = normMat_info[ getFacInfo()[i][0]];
            Vector3d v2 = normMat_info[ getFacInfo()[i][1]];
            Vector3d v3 = normMat_info[ getFacInfo()[i][2]];
            if ( v1.length() >= 1.01 || v1.length() <= 0.99) {
                System.out.println("error in v1 length as:");
                System.out.println(v1.x +" "+ v1.y + " " +v1.z);
                System.out.println(v1.length());
            }
            if ( v2.length() >= 1.01 || v2.length() <= 0.99) {
                System.out.println("error in v2 length as:");
                System.out.println(v2.x +" "+ v2.y + " " +v2.z);
                System.out.println(v2.length());
            }
            if ( v3.length() >= 1.01 || v3.length() <= 0.99) {
                System.out.println("error in v3 length as:");
                System.out.println(v3.x +" "+ v3.y + " " +v3.z);
                System.out.println(v3.length());
            }

            GL11.glNormal3d( v1.x, v1.y, v1.z);
            GL11.glVertex3d( p1.x, p1.y, p1.z);
            GL11.glNormal3d( v2.x, v2.y, v2.z);
            GL11.glVertex3d( p2.x, p2.y, p2.z);
            GL11.glNormal3d( v3.x, v3.y, v3.z);
            GL11.glVertex3d( p3.x, p3.y, p3.z);

            GL11.glEnd();
        }
        GL11.glDisable(GL11.GL_LIGHTING);
    }


    public MStickObj4Smooth()
    {
        nComponent = 1;
        setnVect(0); setnFac(0);
    }
    /**
     Constructor, use a TubeComp to be set as the first component of this MStickSMooth object
     */
    public MStickObj4Smooth( TubeComp in_comp)
    {
        boolean showDebug = false;
        nComponent = 1;
        comp = new TubeComp[MAX_COMP];
        comp[1] = in_comp; // here we use the loose copy ( which should be fine)

        //hard copy the vect, normMat, fac info from first tube to the object
        int i, j;
        this.setnVect(in_comp.getnVect());
        this.setnFac(in_comp.getnFac());
        if (showDebug)
            System.out.println("the new obj with vec :" + getnVect() + " n face " + getnFac());
        for (i=1; i<= in_comp.getnVect(); i++)
        {
            vect_info[i] = new Point3d( in_comp.getVect_info()[i]);
            normMat_info[i] = new Vector3d( in_comp.getNormMat_info()[i]);

            vectTag[i] = 1;
        }
        for (i=0; i< in_comp.getnFac(); i++)
            for (j=0; j<3; j++)
                getFacInfo()[i][j] = in_comp.getFacInfo()[i][j];

        this.setMaxXYZ(new Point3d( in_comp.getMaxXYZ()));
        this.setMinXYZ(new Point3d( in_comp.getMinXYZ()));
    }



    /**
     subFunction of objectMerge, doing the part of merging vect and fac info from <BR>
     two original objects and IntersectPatch
     */
    private void objectMerge_SUB_CombineVect(MStickObj4Smooth inObj, MStickObj4Smooth IntersectPatch)
    {
        boolean showDebug = false;
        int i, j;
        // vect, normMat generation
        int[] MapObj1 = new int[this.getnVect() +1];
        int[] MapObj2 = new int[inObj.getnVect() +1];
        int[] MapObj3 = new int[IntersectPatch.getnVect() +1];
        Point3d[] newVect = new Point3d[15000];
        Vector3d[] newNormMat = new Vector3d[15000];
        int[] newVectTag = new int[15000];
        int nNewVect = 1;
        Point3d[] boundPtData = new Point3d[3000];
        int[] boundPtNdx = new int[3000];
        int nBoundPt = 1;

        this.nIntersectPatch++;

        // 1. put vertex info in obj1 into newVect
        for (i=1; i<= this.getnVect(); i++)
            if ( this.vect_type[i] == 0 || this.vect_type[i] == 3)
            {
                newVect[nNewVect] = new Point3d( this.vect_info[i]);
                newNormMat[nNewVect] = new Vector3d( this.normMat_info[i]);
                newVectTag[nNewVect] = this.vectTag[i];
                MapObj1[i] = nNewVect;
                if ( this.vect_type[i] == 3)
                {
                    newVectTag[nNewVect] = -this.nIntersectPatch;
                    boundPtData[nBoundPt] = new Point3d( this.vect_info[i]);
                    boundPtNdx[nBoundPt] = nNewVect;
                    nBoundPt++;
                }
                nNewVect++;
            }

        // 2. put vertex info in obj2 into newVect
        for (i=1; i<= inObj.getnVect(); i++)
            if ( inObj.vect_type[i] == 0 || inObj.vect_type[i] == 3)
            {
                newVect[nNewVect] = new Point3d( inObj.vect_info[i]);
                newNormMat[nNewVect] = new Vector3d( inObj.normMat_info[i]);
                newVectTag[nNewVect] = this.nComponent+1;
                MapObj2[i] = nNewVect;
                if ( inObj.vect_type[i] == 3)
                {
                    newVectTag[nNewVect] = - this.nIntersectPatch;
                    boundPtData[nBoundPt] = new Point3d( inObj.vect_info[i]);
                    boundPtNdx[nBoundPt] = nNewVect;
                    nBoundPt++;
                }
                nNewVect++;
            }

        // 3. put vertex info in intersectBound into newVect, need to check for redundant pt
        Point3d nowp, nowq;
        double dist;
        boolean redun_flag;
        int nRedun = 0;
        for (i=1; i<= IntersectPatch.getnVect(); i++)
        {
            nowp = IntersectPatch.vect_info[i];
            redun_flag = false; // redundant pt or not
            for (j=1; j< nBoundPt; j++)
            {
                nowq = boundPtData[j];
                dist = nowp.distance(nowq);
                if ( dist <= 0.0001)
                {
                    MapObj3[i] = boundPtNdx[j];
                    redun_flag = true;
                    nRedun ++;
                    break;
                }
            }

            if (!redun_flag) // a new pt
            {
                newVect[nNewVect] = new Point3d( IntersectPatch.vect_info[i]);
                newNormMat[nNewVect] = new Vector3d( IntersectPatch.normMat_info[i]);
                MapObj3[i] = nNewVect;
                newVectTag[nNewVect] = - this.nIntersectPatch;
                nNewVect++;
            }

        }
        nNewVect--; // -1 since we over count 1
        if (showDebug)
        {
            System.out.println("\n\nOBJECT MERGE INFO SUMMARY:\n======================================");
            System.out.println("nVect in intersect " + IntersectPatch.getnVect());
            System.out.println("nRedun found is " + nRedun);
            System.out.println("n NewVect is " + nNewVect);
            System.out.println("nVect obj1 "+ this.getnVect() + "  nvect obj2 " + inObj.getnVect() + "  interboundPt " + IntersectPatch.getnVect());
            System.out.println("nfac obj1 "+ this.getnFac() + "  nFac obj2 " + inObj.getnFac() + "  interboundPt " + IntersectPatch.getnFac());
        }
        // Fac generation
        int[][] newFac = new int[25000][3];
        int nNewFac = 0;
        // From obj1
        for (i=0; i < this.getnFac(); i++)
            if ( (this.vect_type[ this.getFacInfo()[i][0]] == 0 || this.vect_type[ this.getFacInfo()[i][0]] == 3 ) &&
                    (this.vect_type[ this.getFacInfo()[i][1]] == 0 || this.vect_type[ this.getFacInfo()[i][1]] == 3 ) &&
                    (this.vect_type[ this.getFacInfo()[i][2]] == 0 || this.vect_type[ this.getFacInfo()[i][2]] == 3 ) )
            {
                newFac[nNewFac][0] = MapObj1[this.getFacInfo()[i][0]];
                newFac[nNewFac][1] = MapObj1[this.getFacInfo()[i][1]];
                newFac[nNewFac][2] = MapObj1[this.getFacInfo()[i][2]];
                nNewFac++;
            }

        // From obj2
        for (i=0; i < inObj.getnFac(); i++)
            if ( (inObj.vect_type[ inObj.getFacInfo()[i][0]] == 0 || inObj.vect_type[ inObj.getFacInfo()[i][0]] == 3 ) &&
                    (inObj.vect_type[ inObj.getFacInfo()[i][1]] == 0 || inObj.vect_type[ inObj.getFacInfo()[i][1]] == 3 ) &&
                    (inObj.vect_type[ inObj.getFacInfo()[i][2]] == 0 || inObj.vect_type[ inObj.getFacInfo()[i][2]] == 3 ) )
            {
                newFac[nNewFac][0] = MapObj2[inObj.getFacInfo()[i][0]];
                newFac[nNewFac][1] = MapObj2[inObj.getFacInfo()[i][1]];
                newFac[nNewFac][2] = MapObj2[inObj.getFacInfo()[i][2]];
                nNewFac++;
            }

        //From intersectPatch
        for (i=0; i < IntersectPatch.getnFac(); i++)
        {
            newFac[nNewFac][0] = MapObj3[IntersectPatch.getFacInfo()[i][0]];
            newFac[nNewFac][1] = MapObj3[IntersectPatch.getFacInfo()[i][1]];
            newFac[nNewFac][2] = MapObj3[IntersectPatch.getFacInfo()[i][2]];
            nNewFac++;
        }

        //copy all the important info back into This obj
        this.setnVect(nNewVect);
        this.setnFac(nNewFac);
        for (i=1; i<= getnVect(); i++)
        {
            this.vect_info[i] = new Point3d( newVect[i]);
            this.normMat_info[i] = new Vector3d( newNormMat[i]);
            this.vect_type[i] = 0;
            this.vectTag[i] = newVectTag[i];
        }
        for (i=0; i< getnFac(); i++)
            for (j=0; j<3; j++)
                this.getFacInfo()[i][j] = newFac[i][j];
    }

    /**
     Smooth the vertex of the triangle mesh
     */

    public void smoothVertexAndNormMat(int Vtimes, int Ntimes)
    {
        //nVect, nFac
        // First, generate a matrix called edge_info, which will store the nearby pts to each vertex
        int i, j, p1, p2, p3, now_nEdge;
        int[][] edge_info = new int[getnVect() +1][400];
        int[] nEdgeList= new int[getnVect() +1];
        int smooth_ticker;
        boolean flag;
        int nedge;
        // 1. calculate the edge information
        for (i=0; i < getnFac(); i++)
        {
            p1 = getFacInfo()[i][0];
            p2 = getFacInfo()[i][1];
            p3 = getFacInfo()[i][2];
            // adding p1
            nedge = nEdgeList[p1];

            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p1][j] == p2)
                        flag = false;
                if ( flag )
                {
                    edge_info[p1][nedge] = p2;
                    nedge++;
                }
            }

            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p1][j] == p3)
                        flag = false;
                if ( flag )
                {
                    edge_info[p1][nedge] = p3;
                    nedge++;
                }
            }
            nEdgeList[p1] = nedge;

            // adding p2
            nedge = nEdgeList[p2];

            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p2][j] == p1)
                        flag = false;
                if ( flag )
                {
                    edge_info[p2][nedge] = p1;
                    nedge++;
                }
            }

            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p2][j] == p3)
                        flag = false;
                if ( flag )
                {
                    edge_info[p2][nedge] = p3;
                    nedge++;

                }
            }
            nEdgeList[p2] = nedge;

            // adding p3
            nedge = nEdgeList[p3];

            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p3][j] == p1)
                        flag = false;
                if ( flag )
                {
                    edge_info[p3][nedge] = p1;
                    nedge++;
                }
            }

            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p3][j] == p2)
                        flag = false;
                if ( flag )
                {
                    edge_info[p3][nedge] = p2;
                    nedge++;
                }
            }
            nEdgeList[p3] = nedge;
        }


        // form for sfactor
        double[] sfactorMap = new double[401];
        //sfactorMap[1-2] = 0.0
        sfactorMap[3] = 3.0/16.0;
        for (i=4; i<=400; i++)
            sfactorMap[i] = 1.0/(double)i * (5.0/8.0 - (3.0/8.0 + 1.0/4.0 * Math.cos(2.0*Math.PI/(double)i) *
                    Math.cos(2.0*Math.PI/(double)i))) ;
        // Now, after generation the edge relation, we can run the local vertex average
        {
            Point3d[] newVertex = new Point3d[getnVect() +1];
            Point3d nowVertex = new Point3d();
            for (i=1; i<= getnVect(); i++)
                newVertex[i] = new Point3d();
            for ( smooth_ticker=1; smooth_ticker <= Vtimes; smooth_ticker++)
            {
                for (i=1; i <= getnVect(); i++)
                {
                    now_nEdge = nEdgeList[i];
                    //System.out.println("vect " + i + " with edge " + now_nEdge);
                    nowVertex.set(0.0, 0.0, 0.0);
                    for (j=0; j< now_nEdge; j++)
                    {
                        nowVertex.add( vect_info[ edge_info[i][j]]);
                    }
                    nowVertex.scale( sfactorMap[now_nEdge]);
                    newVertex[i].scaleAdd(1.0 - now_nEdge * sfactorMap[now_nEdge], vect_info[i], nowVertex);
                    if (now_nEdge <= 2)
                        System.out.println("FIND ERROR in smooth Vertex, a point with edge <=2");

                }

                for (i=1; i<= getnVect(); i++)
                    vect_info[i].set( newVertex[i]);

            }

        }


        {
            // now, smooth the normMat
            Vector3d[] newNorm = new Vector3d[getnVect() +1];
            Vector3d nowNorm = new Vector3d();
            for (i=1; i<= getnVect(); i++)
                newNorm[i] = new Vector3d();

            for (smooth_ticker = 1 ; smooth_ticker <= Ntimes ; smooth_ticker++)
            {
                for (i=1; i <= getnVect(); i++)
                {
                    now_nEdge = nEdgeList[i];
                    nowNorm.set(0.0, 0.0, 0.0);
                    for (j=0; j< now_nEdge; j++)
                    {
                        nowNorm.add( normMat_info[ edge_info[i][j]]);
                    }
                    nowNorm.scale( sfactorMap[now_nEdge]);
                    newNorm[i].scaleAdd(1.0 - now_nEdge * sfactorMap[now_nEdge], normMat_info[i], nowNorm);

                    newNorm[i].normalize();
                }

                for (i=1; i<= getnVect(); i++)
                {

                    normMat_info[i].set( newNorm[i]);
                }
            }


        }



    }


    /**
     The MStickObj4Smooth take another object in(which prob. an one tube object). <BR>
     Do the smooth connection btw the two Object, save result into current Obj
     */
    public boolean objectMerge( MStickObj4Smooth inObj, boolean specialTreat)
    {
        // two main roles here are this (1) & inObj (2)
        boolean showDebug = false;
        if (showDebug)
        {
            System.out.println("start merging object procedure....\n\n");
        }
        // 1. distance calculation
        double[] distVec1 = new double[this.getnVect() +1];
        double[] distVec2 = new double[inObj.getnVect() +1];
        distVec1 = MStickObj4Smooth_staticLib.distBtwObj( this, inObj, specialTreat);
        distVec2 = MStickObj4Smooth_staticLib.distBtwObj( inObj, this, specialTreat);

        //debug,this is only active when we try to merge the shape in posthoc of N78
//        if ( specialTreat == true)
//        {
//            System.out.println("nV in inObj" + inObj.nVect);
//            for (int i = 1; i<=inObj.nVect; i++)
//                distVec2[i] = 1.2;
//            //for (int i= inObj.nVect - 450; i<=inObj.nVect; i++)
//            for (int i= 1; i<=450; i++)
//            {
//                distVec2[i] = 0.6;
//            }
//
//        }
        // 2. calculate intersect boundary & boundary rim stitch

        // safety check,if the distVec are all large, which mean this two component not touching actually
        {
            double minDist = 100.0;
            int i;
            for (i=1 ; i<= getnVect(); i++) {
                if (distVec1[i] < minDist) {
                    minDist = distVec1[i];
                }
            }
//            System.out.println(minDist);
//            if (minDist >= 1.2)
            if (minDist >= 3.5)
            {

                System.out.println("The two tube are not contacting.....fail");
                return false; //AC test disable
            }
        }



        //System.out.println("before calc boundary nVect, nFac"+ this.nVect +" "+ this.nFac);
        MStickObj4Smooth IntersectPatch = new MStickObj4Smooth();
        IntersectPatch = MStickObj4Smooth_staticLib.calcIntersectPatch( this, inObj, distVec1, distVec2);

        //debug
        // if (nComponent == 1)
        // {
        //  int i, j;
        //  this.nVect = IntersectPatch.nVect;
        //  this.nFac = IntersectPatch.nFac;
        //  for (i=1; i<=nVect; i++)
        //  {
        //      vect_info[i] = IntersectPatch.vect_info[i];
        //      normMat_info[i] = IntersectPatch.normMat_info[i];
        //      vect_type[i] = 0;
        //  }
        //  for (i=0; i< nFac; i++)
        //      for (j=0; j<3; j++)
        //          this.facInfo[i][j] = IntersectPatch.facInfo[i][j];
        //  return;
        // }
        //





        if (IntersectPatch.getnVect() == -1) {// don't do anymore
            if (showDebug){
                System.out.println("fail intersectPatch.nvect ==-1");
            }
            return false; //AC TEST DISABLE
        }


        // 3. now the important part
        // merge the mesh from this, inObj, and IntersectPatch into one water-tight mesh
        this.objectMerge_SUB_CombineVect(inObj, IntersectPatch);

        // 4. update some object information
        // we assume the inObj is a one component object
        this.nComponent++;
        this.comp[nComponent] = inObj.comp[1];

        // update AABB

//        if (inObj.minXYZ.getX() < this.minXYZ.getX())  this.minXYZ.setX( inObj.minXYZ.getX());
//        if (inObj.minXYZ.getY() < this.minXYZ.getY())  this.minXYZ.setY( inObj.minXYZ.getY());
//        if (inObj.minXYZ.getZ() < this.minXYZ.getZ())  this.minXYZ.setZ( inObj.minXYZ.getZ());
//
//        if (inObj.maxXYZ.getX() > this.maxXYZ.getX())  this.maxXYZ.setX( inObj.maxXYZ.getX());
//        if (inObj.maxXYZ.getY() > this.maxXYZ.getY())  this.maxXYZ.setY( inObj.maxXYZ.getY());
//        if (inObj.maxXYZ.getZ() > this.maxXYZ.getZ())  this.maxXYZ.setZ( inObj.maxXYZ.getZ());


        if (inObj.getMinXYZ().x < this.getMinXYZ().x)  this.getMinXYZ().x =  inObj.getMinXYZ().x;
        if (inObj.getMinXYZ().y < this.getMinXYZ().y)  this.getMinXYZ().y =  inObj.getMinXYZ().y;
        if (inObj.getMinXYZ().z < this.getMinXYZ().z)  this.getMinXYZ().z =  inObj.getMinXYZ().z;

        if (inObj.getMaxXYZ().x > this.getMaxXYZ().x)  this.getMaxXYZ().x =  inObj.getMaxXYZ().x;
        if (inObj.getMaxXYZ().y > this.getMaxXYZ().y)  this.getMaxXYZ().y =  inObj.getMaxXYZ().y;
        if (inObj.getMaxXYZ().z > this.getMaxXYZ().z)  this.getMaxXYZ().z =  inObj.getMaxXYZ().z;

        return true;
    }

    /**
     check the orientation of the triangle if it has the normal point outside
     */
    public void triangleOrientationCheck()
    {
        //rotate the points on fac if it is not CCW
        Point3d p1, p2, p3;
        Vector3d norm1, vec1 = new Vector3d(), vec2 = new Vector3d(), crossP = new Vector3d();
        int i;
        for (i=0; i< this.getnFac(); i++)
        {
            p1 = vect_info[ getFacInfo()[i][0]];
            p2 = vect_info[ getFacInfo()[i][1]];
            p3 = vect_info[ getFacInfo()[i][2]];
            norm1 = new Vector3d();
            norm1.add( normMat_info[ getFacInfo()[i][0]], normMat_info[getFacInfo()[i][1]]);
            norm1.add( normMat_info[ getFacInfo()[i][2]]);
            norm1.normalize();
            vec1.sub(p2, p1);
            vec2.sub(p3, p1);
            crossP.cross( vec1,vec2);
            if  ( crossP.dot(norm1) < 0) // need chg
            {
                //System.out.println("a triangle need to be flipped");
                int temp = getFacInfo()[i][1];
                getFacInfo()[i][1] = getFacInfo()[i][2]; getFacInfo()[i][2] = temp;
            }

        }



    }


    /**
     A function that will densify each triangle faces into 4 triangle faces
     It will be used in IntersectPatch
     */
    public void densifyPatch()
    {
        int i, j;
        boolean flag;
        int[] nEdgeList = new int[ getnVect() +1];
        int[][] edge_info = new int[getnVect() +1][120];
        int[][] newVect_edge = new int[getnVect() +1][120];
        int p1, p2, p3, nedge;
        // 1. calculate the edge information
        for (i=0; i < getnFac(); i++)
        {
            p1 = getFacInfo()[i][0];
            p2 = getFacInfo()[i][1];
            p3 = getFacInfo()[i][2];
            // adding p1
            nedge = nEdgeList[p1];
            if ( p2 > p1)
            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p1][j] == p2)
                        flag = false;
                if ( flag )
                {
                    edge_info[p1][nedge] = p2;
                    nedge++;
                }
            }
            if ( p3 > p1)
            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p1][j] == p3)
                        flag = false;
                if ( flag )
                {
                    edge_info[p1][nedge] = p3;
                    nedge++;
                }
            }
            nEdgeList[p1] = nedge;

            // adding p2
            nedge = nEdgeList[p2];
            if ( p1 > p2)
            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p2][j] == p1)
                        flag = false;
                if ( flag )
                {
                    edge_info[p2][nedge] = p1;
                    nedge++;
                }
            }
            if ( p3 > p2)
            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p2][j] == p3)
                        flag = false;
                if ( flag )
                {
                    edge_info[p2][nedge] = p3;
                    nedge++;

                }
            }
            nEdgeList[p2] = nedge;

            // adding p3
            nedge = nEdgeList[p3];
            if ( p1 > p3)
            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p3][j] == p1)
                        flag = false;
                if ( flag )
                {
                    edge_info[p3][nedge] = p1;
                    nedge++;
                }
            }
            if ( p2 > p3)
            {
                flag = true;
                for (j=0; j< nedge; j++)
                    if (edge_info[p3][j] == p2)
                        flag = false;
                if ( flag )
                {
                    edge_info[p3][nedge] = p2;
                    nedge++;
                }
            }
            nEdgeList[p3] = nedge;
        }

        int newNVect = this.getnVect();
        Point3d[] newVect = new Point3d[ this.getnVect() *3 + 1];
        Vector3d[] newNormMat = new Vector3d[ this.getnVect() *3 + 1];
        int[][] newFac = new int[getnFac() * 4][3];

        // 2. adding new intermediate vect
        for (i=1; i<= getnVect(); i++)
        {
            nedge = nEdgeList[i];
            p1 = i;
            for (j=0; j< nedge; j++)
            {
                p2 = edge_info[p1][j];
                newNVect++;
                newVect_edge[p1][j] = newNVect;

                newVect[newNVect] = new Point3d();
                //System.out.println("p1 p2 " + p1 + " " +p2);
                newVect[newNVect].add( vect_info[p1], vect_info[p2]);
                newVect[newNVect].scale(0.5);

                newNormMat[newNVect] = new Vector3d();
                newNormMat[newNVect].add( normMat_info[p1], normMat_info[p2]);
                newNormMat[newNVect].normalize();

            }
        }
//      System.out.println( "length by math " + newVect.length);
//      System.out.println(" by counter " + newNVect);
        // 3. calculate the new fac
        int f_adder;
        int pa, pb, p4, p5, p6;
        for (i = 0; i < getnFac(); i++)
        {
            f_adder = (i)*4;
            p1 = getFacInfo()[i][0]; p2 = getFacInfo()[i][1]; p3 = getFacInfo()[i][2];
            // pick p4
            if (p1 < p2)
            { pa = p1; pb = p2;}
            else
            { pa = p2; pb = p1;}
            for (j=0; j< nEdgeList[pa]; j++)
                if (edge_info[pa][j] == pb)
                    break;
            p4 = newVect_edge[pa][j];

            // pick p5
            if (p2 < p3)
            { pa = p2; pb = p3;}
            else
            { pa = p3; pb = p2;}
            for (j=0; j< nEdgeList[pa]; j++)
                if (edge_info[pa][j] == pb)
                    break;
            p5 = newVect_edge[pa][j];

            // pick p6
            if (p1 < p3)
            { pa = p1; pb = p3;}
            else
            { pa = p3; pb = p1;}
            for (j=0; j< nEdgeList[pa]; j++)
                if (edge_info[pa][j] == pb)
                    break;
            p6 = newVect_edge[pa][j];

            newFac[0+f_adder][0] = p1; newFac[0+f_adder][1] = p4; newFac[0+f_adder][2] = p6;
            newFac[1+f_adder][0] = p4; newFac[1+f_adder][1] = p2; newFac[1+f_adder][2] = p5;
            newFac[2+f_adder][0] = p5; newFac[2+f_adder][1] = p3; newFac[2+f_adder][2] = p6;
            newFac[3+f_adder][0] = p6; newFac[3+f_adder][1] = p4; newFac[3+f_adder][2] = p5;
        }
        // 4. copy the new data into the object's storage

        // 4.1 update vect, normMat
        for (i= getnVect() +1; i<= newNVect; i++)
        {
            this.vect_info[i] = new Point3d( newVect[i]);
            this.normMat_info[i] = new Vector3d( newNormMat[i]);
        }
        // 4.2 update fac
        for (i=0; i< getnFac() *4; i++)
            for (j=0; j<3; j++)
            {
                this.getFacInfo()[i][j] = newFac[i][j];
            }
        this.setnVect(newNVect);
        this.setnFac(getnFac() *4);
    }

    /**
     *    Oct 2nd 2008.
     *    this is a function that will be called by MatchStick.
     *    Here, we will examine all the vertex on the object, and see which one is qualify the following:
     *    |x| < N , |y| <N, Max(z).
     *    That is, intuitively, the surface point most near the viewer (without much rotation)
     */
    public Point3d translateVertexOnZ(double scaleForMAxisShape) {
        boolean showDebug = false;
        // the tolerance should depends on the scaleForMAxisShape
        double tolerance = 0.1 * scaleForMAxisShape; //this is debatable, and should be extensible (if original version not good)
        int i;
        if ( showDebug)
            System.out.println("start translate on Z to make fixation on surface");
        //1. pick the point most near to viewr
        Point3d nearestPt = new Point3d(0.0, 0.0, 0.0);

        for (tolerance = 0.2 * scaleForMAxisShape; tolerance <=1.0 * scaleForMAxisShape; tolerance+= 0.1* scaleForMAxisShape)
        {
            if ( showDebug)
                System.out.println("now using tolerance at " + tolerance);
            nearestPt.set(0.0, 0.0, 0.0);
            for (i=1; i<= getnVect(); i++)
            {
                if ( vect_info[i].x < tolerance && vect_info[i].x > -tolerance)
                    if ( vect_info[i].y < tolerance && vect_info[i].y > -tolerance)
                        if (vect_info[i].z > nearestPt.z)
                        {
                            Vector3d nowVec = new Vector3d(0,0,1);
                            Vector3d tarVec = new Vector3d( vect_info[i]);
                            double ang = nowVec.angle( tarVec);
                            if ( ang <= Math.PI * 0.5)
                                nearestPt.set( vect_info[i]);
                        }
            }
            if ( nearestPt.z > 0.0)
            {
                break;
            }
        }
        if ( showDebug)
            System.out.println("we choose the nearest pt"+ nearestPt.toString());
        //2. translate all vertex with the shiftVector
        for (i=1; i<= getnVect(); i++)
        {
            vect_info[i].sub(nearestPt);
        }

        Point3d translateVector = new Point3d(
                -nearestPt.x, -nearestPt.y, -nearestPt.z);
        return translateVector;
    }

    public Point3d translateVertexOnZ_ram() {
        int i;

        Point3d nearestPt = new Point3d(0.0, 0.0, 0.0);
        Point3d farthestPt = new Point3d(0.0, 0.0, 0.0);

        double maxZ = -1000;
        double minZ = 1000;

        for (i=1; i<= getnVect(); i++) {
            maxZ = Math.max(vect_info[i].z,maxZ);
            minZ = Math.min(vect_info[i].z,maxZ);
        }

        nearestPt.z = maxZ;
        farthestPt.z = minZ;



        for (i=1; i<= getnVect(); i++) {
            vect_info[i].sub(nearestPt);
        }
        return nearestPt;
    }

    public Point3d subCenterOfMass() {
        Point3d[] box = getBoundingBox();
        Point3d center = new Point3d((box[1].x+box[0].x)/2,(box[1].y+box[0].y)/2,(box[1].z+box[0].z)/2);

        for (int i = 1; i<= getnVect(); i++) {
            vect_info[i].sub(center);
        }
        return center;
    }

    public Point3d[] getBoundingBox() {
        Point3d[] box = new Point3d[2];
        box[0] = new Point3d(5000,5000,5000);
        box[1] = new Point3d(-5000,-5000,-5000);

        for (int i = 1; i<= getnVect(); i++) {
            Point3d p1 = vect_info[i];

            box[1].x = Math.max(box[1].x, p1.x);
            box[1].y = Math.max(box[1].y, p1.y);
            box[1].z = Math.max(box[1].z, p1.z);

            box[0].x = Math.min(box[0].x, p1.x);
            box[0].y = Math.min(box[0].y, p1.y);
            box[0].z = Math.min(box[0].z, p1.z);
        }
        return box;
    }



    /**
     *   This function is actually not in use
     *   it was substituted by another function in MatchStick.java
     */
    public boolean finalSizeCheck() {
        /// Dec 18th 2008
        ///This is a final check of the size of stimulus
        double minLimit = 34.9040/4; // 4deg - min should be 1 deg: RAM
        double maxLimit = 87.26; // 10 deg

        double cubeSize = maxLimit / 2.0;
        double sm_cube = minLimit / 2.0;
        int i; // j;

        double maxX, maxY;
        double minX, minY;
        maxX = -100.0; maxY = -100.0;
        minX = 100.0; minY = 100.0;

        for (i=1; i<= this.getnVect(); i++)
        {
            if (this.vect_info[i].x > cubeSize || this.vect_info[i].x < -cubeSize)
                return false;
            if ( this.vect_info[i].y > cubeSize || this.vect_info[i].y < -cubeSize)
                return false;

            if (vect_info[i].x > maxX) maxX = vect_info[i].x;
            if ( vect_info[i].x < minX) minX = vect_info[i].x;

            if ( vect_info[i].y < maxY) maxY = vect_info[i].y;
            if ( vect_info[i].y < minY) minY = vect_info[i].y;

        }

        //debug, show max min
        System.out.println("Max: "+ maxX + "  "+ maxY );
        System.out.println("Min: "+ minX + "  "+ minY  +"\n") ;



        //we need to think more of this

        if ( (maxX < sm_cube&& minX > -sm_cube ) &&
                (maxY < sm_cube && minY > -sm_cube)  )

        {
            System.out.println("IN FINAL SIZE CHK");
            System.out.println("the shape is too small by small cube cond");
            return true;
        }

        // 2 out of 3 dimension less than minLimit
        /*
        if ( (xRange < minLimit && yRange < minLimit) ||
              (xRange < minLimit && zRange < minLimit) ||
              (yRange < minLimit && zRange < minLimit) ) // both x,y dim are small
        {
            System.out.println("this is a small shape, no good");
            System.out.println("limit is " + minLimit);
            System.out.println("range x,y,z " + xRange + " " + yRange + " " + zRange);
            return true;
        }
        */

        return true;
    }

    boolean isDoLighting() {
        return doLighting;
    }

    public int getnVect() {
        return nVect;
    }

    public int getnFac() {
        return nFac;
    }

    void setDoLighting(boolean doLighting) {
        this.doLighting = doLighting;
    }

    public int[][] getFacInfo() {
        return facInfo;
    }

    public void setFacInfo(int[][] facInfo) {
        this.facInfo = facInfo;
    }

    public void setnVect(int nVect) {
        this.nVect = nVect;
    }

    public void setnFac(int nFac) {
        this.nFac = nFac;
    }

    public Point3d getMinXYZ() {
        return minXYZ;
    }

    public void setMinXYZ(Point3d minXYZ) {
        this.minXYZ = minXYZ;
    }

    public Point3d getMaxXYZ() {
        return maxXYZ;
    }

    public void setMaxXYZ(Point3d maxXYZ) {
        this.maxXYZ = maxXYZ;
    }

    public RGBColor getStimColor() {
        return stimColor;
    }

    public void setStimColor(RGBColor stimColor) {
        this.stimColor = stimColor;
    }
}

/**
 class that store the intersect boundary info of an MStickobj4Smooth
 */
class IntersectBoundaryInfo {
    // should include the outerRim info & the vect_type info
    public int nRimPt;
    public Point3d[] rim_Pt;
    public Point3d[] rim_Pt_smoothed;
    public Vector3d[] rim_normMat;

    public void setInfo(int in_nRimPt, int[] rimPtList, MStickObj4Smooth obj)
    {
        int i;

        nRimPt = in_nRimPt;

        rim_Pt = new Point3d[nRimPt+2];
        rim_normMat = new Vector3d[nRimPt+2];
        rim_Pt_smoothed = new Point3d[nRimPt+2];
        //System.out.println("set Intersect bound info");
        for (i=1; i<= nRimPt; i++)
        {

            rim_Pt[i] = new Point3d( obj.vect_info[ rimPtList[i]]);
            rim_normMat[i] = new Vector3d( obj.normMat_info[ rimPtList[i]]);
            rim_Pt_smoothed[i] = new Point3d( obj.vect_info[ rimPtList[i]]);
        }

        //System.out.println("start smooth");
        // we can smooth the rim once we setInfo
        this.smoothRim();
    }

    private void smoothRim()
    {
        int time2Smooth = 4;
        int i, j;
        Point3d[] newPt = new Point3d[ nRimPt + 2];
        for (i=1; i<= nRimPt; i++)
            newPt[i] = new Point3d();



        for (j=1; j<= time2Smooth; j++)
        {
            for (i=1; i<= nRimPt; i++)
            {
              /*
              if (i == 1)
              {
                newPt[i].setX( (rim_Pt_smoothed[i].getX() + rim_Pt_smoothed[i+1].getX() + rim_Pt_smoothed[nRimPt].getX() ) / 3.0);
                newPt[i].setY( (rim_Pt_smoothed[i].getY() + rim_Pt_smoothed[i+1].getY() + rim_Pt_smoothed[nRimPt].getY() ) / 3.0);
                newPt[i].setZ( (rim_Pt_smoothed[i].getZ() + rim_Pt_smoothed[i+1].getZ() + rim_Pt_smoothed[nRimPt].getZ() ) / 3.0);
              }
              else if ( i == nRimPt)
              {
                  newPt[i].setX( (rim_Pt_smoothed[i].getX() + rim_Pt_smoothed[i-1].getX() + rim_Pt_smoothed[1].getX() ) / 3.0);
                  newPt[i].setY( (rim_Pt_smoothed[i].getY() + rim_Pt_smoothed[i-1].getY() + rim_Pt_smoothed[1].getY() ) / 3.0);
                  newPt[i].setZ( (rim_Pt_smoothed[i].getZ() + rim_Pt_smoothed[i-1].getZ() + rim_Pt_smoothed[1].getZ() ) / 3.0);
              }
              else
              {
                  newPt[i].setX( (rim_Pt_smoothed[i].getX() + rim_Pt_smoothed[i+1].getX() + rim_Pt_smoothed[i-1].getX() ) / 3.0);
                  newPt[i].setY( (rim_Pt_smoothed[i].getY() + rim_Pt_smoothed[i+1].getY() + rim_Pt_smoothed[i-1].getY() ) / 3.0);
                  newPt[i].setZ( (rim_Pt_smoothed[i].getZ() + rim_Pt_smoothed[i+1].getZ() + rim_Pt_smoothed[i-1].getZ() ) / 3.0);
              }
              */
                if (i == 1)
                {
                    newPt[i].x = (rim_Pt_smoothed[i].x + rim_Pt_smoothed[i+1].x + rim_Pt_smoothed[nRimPt].x ) / 3.0;
                    newPt[i].y =  (rim_Pt_smoothed[i].y + rim_Pt_smoothed[i+1].y + rim_Pt_smoothed[nRimPt].y ) / 3.0;
                    newPt[i].z = (rim_Pt_smoothed[i].z + rim_Pt_smoothed[i+1].z + rim_Pt_smoothed[nRimPt].z ) / 3.0;
                }
                else if ( i == nRimPt)
                {
                    newPt[i].x = (rim_Pt_smoothed[i].x + rim_Pt_smoothed[i-1].x + rim_Pt_smoothed[1].x ) / 3.0;
                    newPt[i].y =  (rim_Pt_smoothed[i].y + rim_Pt_smoothed[i-1].y + rim_Pt_smoothed[1].y ) / 3.0;
                    newPt[i].z = (rim_Pt_smoothed[i].z + rim_Pt_smoothed[i-1].z + rim_Pt_smoothed[1].z ) / 3.0;
                }
                else
                {
                    newPt[i].x = (rim_Pt_smoothed[i].x + rim_Pt_smoothed[i+1].x + rim_Pt_smoothed[i-1].x ) / 3.0;
                    newPt[i].y =  (rim_Pt_smoothed[i].y + rim_Pt_smoothed[i+1].y + rim_Pt_smoothed[i-1].y ) / 3.0;
                    newPt[i].z =  (rim_Pt_smoothed[i].z + rim_Pt_smoothed[i+1].z + rim_Pt_smoothed[i-1].z ) / 3.0;
                }

            }

            for (i=1; i<= nRimPt; i++)
                rim_Pt_smoothed[i].set( newPt[i]);
        }

//      //make a loop
//      rim_Pt[nRimPt+1] = new Point3d( rim_Pt[1]);
//      rim_Pt_smoothed[nRimPt+1] = new Point3d( rim_Pt_smoothed[1]);
//      rim_normMat[nRimPt+1] = new Vector3d( rim_normMat[1]);
    }

}

class MStickObj4Smooth_staticLib {
    /**
     Function that calculate the Intersect patch btw two MStickObj4Smooth <BR>
     This will cover the old Matlab code : (1) calcIntersectBoundary.m <BR>
     (2) boundaryRimStitch.m
     */
    public static MStickObj4Smooth calcIntersectPatch( MStickObj4Smooth obj1, MStickObj4Smooth obj2, double[] distVec1, double[] distVec2)
    {
        // 1. for both obj, calculate intersectBoundary
        IntersectBoundaryInfo interBound_obj1 = new IntersectBoundaryInfo();
        IntersectBoundaryInfo interBound_obj2 = new IntersectBoundaryInfo();

        //System.out.println("calc intersect");
        double threshold_1 = 0.95, threshold_2 = 1.03;
        //NOTE: obj2 should be a one component object
        if (obj2.comp[1].getConnectType() == 4 ) // use the branch to connect up
        {
            threshold_1 = 1.03;
            threshold_2 = 0.95;
            //not very important debug, mark it up (Dec 16 2008)
            //System.out.println("switch threshold");
        } // reverse it

        interBound_obj1 = MStickObj4Smooth_staticLib.calcIntersectBoundary(obj1, distVec1, threshold_1);
        interBound_obj2 = MStickObj4Smooth_staticLib.calcIntersectBoundary(obj2, distVec2, threshold_2);

        //System.out.println("In gen patch" + interBound_obj1.nRimPt + " " + interBound_obj2.nRimPt);


//        if (interBound_obj1.nRimPt == -1) // what we found in N71 posthoc
//        {
//            interBound_obj1 = MStickObj4Smooth_staticLib.calcIntersectBoundary(obj1, distVec1, threshold_1);
//
//
//        }


        if (interBound_obj1.nRimPt == -1 || interBound_obj2.nRimPt == -1) // error occur, in calc Intersect, we'll just give up
        {
            MStickObj4Smooth testPatch = new MStickObj4Smooth();
            testPatch.setnVect(-1);
            return testPatch;
        }

        // 2. stich the boundary rim
        MStickObj4Smooth iPatch = new MStickObj4Smooth();
        iPatch = MStickObj4Smooth_staticLib.boundaryRimStitch(interBound_obj1, interBound_obj2);
        // 3. densify the IntersectPatch

        iPatch.densifyPatch();

        iPatch.triangleOrientationCheck(); // check the orientation of triangles
        //debug
        return iPatch;
    }

    /**
     Given the wo IntersectBoundaryInfo structure, <BR>
     Creating a mesh btw these two closed loop in space
     */
    private static MStickObj4Smooth  boundaryRimStitch(IntersectBoundaryInfo bound_1, IntersectBoundaryInfo bound_2)
    {
        boolean showDebug = false;
        MStickObj4Smooth resObj = new MStickObj4Smooth();
        resObj.setnVect(bound_1.nRimPt + bound_2.nRimPt);
        int[] vectLabel_1 = new int[ bound_1.nRimPt+1];
        int[] vectLabel_2 = new int[ bound_2.nRimPt+1];
        int i, j;
//  public int nRimPt;
//  public Point3d[] rim_Pt;
//  public Point3d[] rim_Pt_smoothed;
//  public Vector3d[] rim_normMat;
        int counter = 1;
        for (i=1; i<= bound_1.nRimPt; i++)
        {
            resObj.vect_info[counter] = new Point3d( bound_1.rim_Pt[i]);
            //resObj.vect_info[counter] = new Point3d( bound_1.rim_Pt_smoothed[i]);
            resObj.normMat_info[counter] = new Vector3d( bound_1.rim_normMat[i]);
            vectLabel_1[i] = counter;
            counter = counter+1;
        }
        for (i=1; i<= bound_2.nRimPt; i++)
        {
            resObj.vect_info[counter] = new Point3d( bound_2.rim_Pt[i]);
            //resObj.vect_info[counter] = new Point3d( bound_2.rim_Pt_smoothed[i]);
            resObj.normMat_info[counter] = new Vector3d( bound_2.rim_normMat[i]);
            vectLabel_2[i] = counter;
            counter = counter+1;
        }
//  System.out.println("nvect by math is " + resObj.nVect);
//  System.out.println("counter res is " + counter);

        // now start doing the stitch, which will generate a fac Map
        int nNode1 = bound_1.nRimPt;
        int nNode2 = bound_2.nRimPt;
        int bestI = -100 , bestJ= -100;

        if (showDebug)
        {
            System.out.println("In rimStich, check if smooth vertex work");
            System.out.println( bound_1.rim_Pt[1] + "\n" + bound_1.rim_Pt[3]);
            System.out.println( bound_1.rim_Pt_smoothed[1] + "\n" + bound_1.rim_Pt_smoothed[3]);
        }
        // 1. find best suited starting point on each ring
        {
            double mindist = 10000.0, nowdist = -1;

            for (i=1; i<= nNode1; i++)
                for (j=1; j<= nNode2; j++)
                {
                    nowdist = bound_1.rim_Pt_smoothed[i].distance( bound_2.rim_Pt_smoothed[j]);
                    if ( nowdist < mindist)
                    {
                        mindist = nowdist;
                        bestI = i; bestJ = j;
                    }
                }
        }
        // 2. check the direction of bound_1 & bound_2, and make list1, list2 which start at bestI & bestJ and go in good direction
        Point3d[] list1 = new Point3d[ nNode1+2];
        Point3d[] list2 = new Point3d[ nNode2+2];
        int[] listLabel_1 = new int[ nNode1+2];
        int[] listLabel_2 = new int[ nNode2+2];
        //System.out.println("nNode1 " + nNode1 + " nNode2 " + nNode2);
        {
            Vector3d ori1 = new Vector3d(), ori2 = new Vector3d(), ori3 = new Vector3d();
            if (bestI == nNode1)
                ori1.sub( bound_1.rim_Pt_smoothed[1] , bound_1.rim_Pt_smoothed[bestI]);
            else
                ori1.sub( bound_1.rim_Pt_smoothed[bestI+1] , bound_1.rim_Pt_smoothed[bestI]);

            if (bestJ == nNode2)
                ori2.sub( bound_2.rim_Pt_smoothed[1] , bound_2.rim_Pt_smoothed[bestJ]);
            else
                ori2.sub( bound_2.rim_Pt_smoothed[bestJ+1] , bound_2.rim_Pt_smoothed[bestJ]);

            if ( bestJ == 1)
                ori3.sub( bound_2.rim_Pt_smoothed[nNode2], bound_2.rim_Pt_smoothed[bestJ]);
            else
                ori3.sub( bound_2.rim_Pt_smoothed[bestJ-1], bound_2.rim_Pt_smoothed[bestJ]);

            boolean InverseFlag;

            double dir1, dir2;
            dir1 = ori1.dot(ori2) / ( ori1.length() * ori2.length());
            dir2 = ori1.dot(ori3) / ( ori1.length() * ori3.length());
//      if (angle1 <= angle2)
            if (dir1 > dir2)
                InverseFlag = false;
            else
                InverseFlag = true;

            // generate list1
            for (i=1; i <= nNode1; i++)
            {
                if ( bestI+i-1 <= nNode1)
                {
                    list1[i] = bound_1.rim_Pt_smoothed[ bestI+i-1]; // soft copy is fine, since we'll not chg value here
                    listLabel_1[i] = vectLabel_1[bestI+i-1];
                }
                else
                {
                    list1[i] = bound_1.rim_Pt_smoothed[ bestI+i-1 - nNode1];
                    listLabel_1[i] = vectLabel_1[ bestI+i-1 - nNode1];
                }
            }

            // generate list2

            if ( InverseFlag == false)
            {
                for (i=1; i<= nNode2; i++)
                {
                    if (bestJ+i-1 <= nNode2)
                    {
                        list2[i] = bound_2.rim_Pt_smoothed[ bestJ+i-1];
                        listLabel_2[i] = vectLabel_2[ bestJ+i-1];
                    }
                    else
                    {
                        list2[i] = bound_2.rim_Pt_smoothed[ bestJ+i-1 - nNode2];
                        listLabel_2[i] = vectLabel_2[bestJ+i-1 - nNode2];
                    }
                }
            }
            else
            {
                for (i=1; i<= nNode2; i++)
                {
                    if ( bestJ-i+1 >= 1 )
                    {
                        list2[i] =  bound_2.rim_Pt_smoothed[bestJ-i+1];
                        listLabel_2[i] = vectLabel_2[bestJ-i+1];
                    }
                    else
                    {
                        list2[i] =  bound_2.rim_Pt_smoothed[ bestJ-i+1 + nNode2];
                        listLabel_2[i] = vectLabel_2[bestJ-i+1 + nNode2];
                    }
                }
            }
        }



        // 3. find a best match face map btw list1 and list2
        {
            int[][] nowFac = new int[2000][3];
            int nFac = 0;
            list1[nNode1+1] = list1[1];
            list2[nNode2+1] = list2[1];
            listLabel_1[nNode1+1] = listLabel_1[1];
            listLabel_2[nNode2+1] = listLabel_2[1];
            int nowV1 = 1, nowV2 = 1;
            double costheta1, costheta2;
            Vector3d vec1 = new Vector3d(), vec2 = new Vector3d();
            while (true)
            {

                if (nowV1 == nNode1+1 && nowV2 == nNode2 +1) break;
                costheta1 = -100; costheta2 = -100;
                if (nowV1 <= nNode1)
                {
                    vec1.sub( list1[nowV1+1] , list1[nowV1]);
                    vec2.sub( list2[nowV2] , list1[nowV1]);

                    costheta1 = (vec1.dot(vec2)) / ( vec1.length() * vec2.length());
                }

                if (nowV2 <= nNode2)
                {
                    vec1.sub( list2[nowV2+1], list2[nowV2]);
                    vec2.sub( list1[nowV1], list2[nowV2]);
                    costheta2 = (vec1.dot(vec2)) / ( vec1.length() * vec2.length());
                }

//          if (angle1 < angle2) //prefer choice 1
                if ( costheta1 > costheta2)
                {
                    nowFac[nFac][0] = listLabel_1[nowV1];
                    nowFac[nFac][1] = listLabel_2[nowV2];
                    nowFac[nFac][2] = listLabel_1[nowV1+1];
                    nFac++;
                    nowV1++;
                }
                else
                {
                    nowFac[nFac][0] = listLabel_2[nowV2];
                    nowFac[nFac][1] = listLabel_1[nowV1];
                    nowFac[nFac][2] = listLabel_2[nowV2+1];

                    nFac++;
                    nowV2++;
                }

            }

            resObj.setnFac(nFac);
            for (i=0; i<nFac; i++)
                for (j=0; j<3; j++)
                    resObj.getFacInfo()[i][j] = nowFac[i][j];
        }



        return resObj;
    }

    /**
     calculate the intersect boundary rim on an object based the distVect info we calculated earlier
     */
    private static IntersectBoundaryInfo calcIntersectBoundary(MStickObj4Smooth obj, double[] distVec, double Threshold)
    {
        boolean showDebug = false;
        double distanceExpand = 0.20; // tricky number??
        int nNodes = obj.getnVect();
        int nFaces = obj.getnFac();
        int[] vect_type = new int[nNodes+1];
        Point3d[] vect = obj.vect_info; // soft copy is fine
        Vector3d[] normMat = obj.normMat_info;
        int[][] facInfo = obj.getFacInfo();
        IntersectBoundaryInfo outerRim = new IntersectBoundaryInfo();
        int i, j;

        //debug
        //     for (i=1; i<= obj.nVect; i++)
        //      if ( distVec[i] != 3.0)
        //          System.out.println(" pt " + i + " dist vec is " + distVec[i]);



        // vect_type value reminder
        // 0 outside
        // -1 : inside
        // 1 : on the inside boundary
        // 2 : nearby Pts
        // 3 : on the outside boundary

        // 1. generate the inside Pt, and interRim Pt
        for ( i = 0; i < nFaces; i++)
        {
            int p1 = facInfo[i][0], p2 = facInfo[i][1], p3 = facInfo[i][2];
            double d1 = distVec[p1], d2 = distVec[p2], d3 = distVec[p3];
            if ( d1 <= Threshold)
            {
                vect_type[p1] = -1;
                if (d2 > Threshold) vect_type[p2] = 1;
                if (d3 > Threshold) vect_type[p3] = 1;
            }
            if ( d2 <= Threshold)
            {
                vect_type[p2] = -1;
                if (d1 > Threshold) vect_type[p1] = 1;
                if (d3 > Threshold) vect_type[p3] = 1;
            }
            if ( d3 <= Threshold)
            {
                vect_type[p3] = -1;
                if (d1 > Threshold) vect_type[p1] = 1;
                if (d2 > Threshold) vect_type[p2] = 1;
            }

        }



        // MATLAB version: boundPt_list = find(vect_type == 1)

        // 2. Calculate points that are nearby to the interRim, so we can eventually generate outerRim
        //    The algorithm applied here is Dijkstra shortest path which make vect_type[p] == 1 Points as source Pt
        int[] nEdgeList = new int[nNodes+1];
        int[][] edge_info = new int[nNodes+1][200];
        //  System.out.println(nNodes);
        double[][] edge_dist = new double[nNodes+1][200];
        {
            int now_nEdge;
            // this for loop generate the basic edge_info we need
            for (i=0; i< nFaces; i++)
            {
                int p1 = facInfo[i][0], p2 = facInfo[i][1], p3 = facInfo[i][2];
                double d12 = vect[p1].distance(vect[p2]);
                double d13 = vect[p1].distance(vect[p3]);
                double d23 = vect[p2].distance(vect[p3]);
                // adding p1's edge info
                now_nEdge = nEdgeList[p1];
                edge_info[p1][now_nEdge] = p2; edge_dist[p1][now_nEdge] = d12;
                edge_info[p1][now_nEdge+1] = p3; edge_dist[p1][now_nEdge+1] = d13;
                nEdgeList[p1] += 2;
                // adding p2's edge info
                now_nEdge = nEdgeList[p2];
                edge_info[p2][now_nEdge] = p1; edge_dist[p2][now_nEdge] = d12;
                edge_info[p2][now_nEdge+1] = p3; edge_dist[p2][now_nEdge+1] = d23;
                nEdgeList[p2] += 2;
                // ading p3's edge info
                now_nEdge = nEdgeList[p3];
                edge_info[p3][now_nEdge] = p1; edge_dist[p3][now_nEdge] = d13;
                edge_info[p3][now_nEdge+1] = p2; edge_dist[p3][now_nEdge+1] = d23;
                nEdgeList[p3] += 2;

            }

            double[] dist2Intersect = new double[nNodes+1];
            boolean[] visited = new boolean[nNodes+1]; // will all be false at first
            for (i=1; i<=nNodes; i++)
            {
                dist2Intersect[i] = 10000.0; // large initialization
                if (vect_type[i] == 1)
                    dist2Intersect[i] = 0.0; // set boundary Pt as source pt.
                if (vect_type[i] == -1) // for inside Pt
                    visited[i] = true;
            }

            double mindist, dist, newdist;
            int nowPt, target;
            while (true)
            {
                // pick unvisited  & minimum distance node out
                mindist = 50000.0;
                nowPt = -1;
                for (i=1; i<=nNodes; i++)
                    if (!visited[i])
                        if (dist2Intersect[i] < mindist)
                        {
                            mindist = dist2Intersect[i];
                            nowPt = i;
                        }
                if (mindist > distanceExpand)
                    break;

                // relax the distance according to Disjkstra's algo
                visited[nowPt] = true;
                now_nEdge = nEdgeList[nowPt];
                for (i=0; i< now_nEdge; i++)
                {
                    target = edge_info[nowPt][i];
                    dist   = edge_dist[nowPt][i];
                    newdist = dist2Intersect[nowPt] + dist;
                    if ( newdist < dist2Intersect[target] && vect_type[target] == 0)
                        dist2Intersect[target] = newdist;
                }

            } // while loop

            for (i=1; i<=nNodes; i++)
                if ( dist2Intersect[i] < distanceExpand && vect_type[i] == 0)
                {
                    vect_type[i] = 2; // set as nearby Pt
                }



        } // a braclet confine the 2nd part of this function


//2.5
//check if all the -1 vertex are all connected as once piece, if not only remain the largest group
        {
            int[] visited = new int[nNodes+1];
            int groupLabel = 2;
            while (true)
            {
                //pick one pt out
                for (i=1; i <= nNodes; i++)
                    if (vect_type[i] == -1 && visited[i] == 0)
                        break;
                if (i == nNodes+1)
                    break;
                int firstPt = i;
                visited[firstPt] = 1;

                boolean haveChg = false;
                while (true)
                {
                    haveChg = false;

                    for (i=1; i<=nNodes; i++)
                        if ( vect_type[i] == -1 && visited[i] == 1)
                        {
                            visited[i] = groupLabel;
                            for (j=0; j < nEdgeList[i]; j++)
                                if (vect_type[ edge_info[i][j]] == -1 && visited[ edge_info[i][j]] == 0)
                                {

                                    visited[ edge_info[i][j]] = 1;
                                    haveChg = true;
                                }
                        }


                    if ( ! haveChg)
                        break;
                }
                groupLabel++;
            }

//   if ( groupLabel == 3)
//  System.out.println("only one group of -1 is found.....");
            boolean test1 = false;
            for (i=1; i<= nNodes; i++)
                if (vect_type[i] == -1 && visited[i] == 0)
                {
                    test1 = true;
                    vect_type[i] = -2;
                    System.out.println("vertex unvisited is " + i + "with distVec " + distVec[i]);
                }
            if (test1)
            {
                System.out.println("WARNING: the -1 zone is NOT a single piece!!\n\n!!\n\n!!");
                outerRim.nRimPt = -1;
                for (i=1; i<=nNodes; i++)
                    obj.vect_type[i] = vect_type[i];
                return outerRim;
            }
            //else
            //System.out.println("WARNING: the -1 zone is OKOKOKOK a single piece!!\n\n!!\n\n!!");
        }
// end of debug











        // 3. calculate the outerRim Pt and make them into an ordered Rim list
        {
            int now_nEdge;
            int target = -1;

            // 3.0 update the inner rim
            for (i=1; i<=nNodes; i++)
                if (vect_type[i] == 1)
                {
                    now_nEdge= nEdgeList[i];
                    boolean flag = false;
                    for (j=0; j< now_nEdge; j++)
                    {
                        target = edge_info[i][j];
                        if ( vect_type[target] == 2 || vect_type[target]== 0)
                            flag = true;
                    }
                    if ( ! flag )
                    {
                        vect_type[i] = -1;
                        //System.out.println("one of inner Pt chged!!!!!!");
                    }
                }
            // 3.1 determine the outerim Pts
            for (i=1; i<=nNodes; i++)
                if (vect_type[i] == 2 || vect_type[i] == 1)
                {
                    now_nEdge = nEdgeList[i];
                    for (j=0; j< now_nEdge; j++)
                    {
                        target = edge_info[i][j];
                        if ( vect_type[target] == 0)
                            vect_type[i] = 3; // on the outer_rim;
                    }
                }
            // 3.2 trim the outerRim to make it a "Sinlge connected Rim"
            boolean valid_flag;
            boolean haveChg = false;
            while (true)
            {
                haveChg = false;
                for (i=1; i <= nNodes; i++) // trim to inside
                    if ( vect_type[i] == 3)
                    {
                        now_nEdge = nEdgeList[i];
                        valid_flag = false;
                        for (j=0; j< now_nEdge; j++)
                        {
                            target = edge_info[i][j];
                            //if ( vect_type[target] == 1 || vect_type[target] == 2 || vect_type[target] == -1)
                            if (vect_type[target] == 0)
                                valid_flag = true;
                        }
                        if (!valid_flag)
                        {
                            vect_type[i] = 2; // set it back to inside Pts if it is not valid
                            //System.out.println("remove one type3 vect to inside");
                            haveChg = true;
                        }
                    }

                for (i=1; i <= nNodes; i++) // trim to outside
                    if ( vect_type[i] == 3)
                    {
                        now_nEdge = nEdgeList[i];
                        valid_flag = false;
                        for (j=0; j< now_nEdge; j++)
                        {
                            target = edge_info[i][j];
                            if ( vect_type[target] == 1 || vect_type[target] == 2 || vect_type[target] == -1)
                                valid_flag = true;
                        }
                        if (!valid_flag)
                        {
                            vect_type[i] = 0; // set it back to outSide Pts if it is not valid
                            //System.out.println("remove one type3 vect to outside, should NOTNOT happen");
                            haveChg = true;
                        }
                    }
                if (!haveChg)
                    break;
                //System.out.println("while loop again!");
            } // while loop
            // 3.3 make the order_OuterRim
            int nOuterRimPt = 0, firstNode = 0;
            boolean[] visited = new boolean[nNodes+1];
            boolean first = true;
            for (i=1; i<= nNodes; i++)
                if (vect_type[i] == 3)
                {
                    if (first)
                    {
                        firstNode = i;
                        first = false;
                    }
                    nOuterRimPt ++;
                    //System.out.println("outrim label :" + i);
                }


            int[] order_OuterRimPt = new int[nOuterRimPt+2];
            order_OuterRimPt[1] = firstNode;
            visited[ order_OuterRimPt[1]] = true;

            //System.out.println("first node is " + firstNode);
            int nowPt;
            int n_Added = 1;
            for (i=2; i<= nOuterRimPt; i++)
            {
                //System.out.print("Now i " + i + " with nhb ");
                now_nEdge = nEdgeList[ order_OuterRimPt[i-1]];
//      for (j=0; j< now_nEdge; j++)
//        if ( vect_type[ edge_info[ order_OuterRimPt[i-1]][j]] == 3)
//              System.out.print( edge_info[ order_OuterRimPt[i-1]][j] + " ");
                for (j=0; j< now_nEdge; j++)
                {
                    nowPt = edge_info[ order_OuterRimPt[i-1]][j];

                    if ( vect_type[nowPt] == 3 && visited[nowPt] == false )
                    {
                        order_OuterRimPt[i] = nowPt;
                        visited[nowPt] = true;
                        n_Added++;
                        //System.out.println("now Add :" + nowPt);
                        break; // break the loop j
                    }
                }
                //System.out.println(" ");
            }

            // debug
            if ( showDebug)
            {
                //System.out.println(" the available # of outerRim Pt is " + nOuterRimPt);
                //System.out.println("nAdded pt on outer rim " + n_Added);
            }
            if ( nOuterRimPt != n_Added)
            {
                if ( showDebug)
                {
                    System.out.println(" the available # of outerRim Pt is " + nOuterRimPt);
                    System.out.println("nAdded pt on outer rim " + n_Added);
                    System.out.println(" discrepancy!!!!!!\n\n");
                }

                for (i=1; i<= nNodes; i++)
                    if (vect_type[i] == 3)
                    {
                        //System.out.println("point " + i +" info ");
                        now_nEdge = nEdgeList[ i];
//            for (j=0; j< now_nEdge; j++)
//            {
//                 if (  vect_type[edge_info[i][j]] == 0 )
//                 if (  vect_type[edge_info[i][j]] == 1 || vect_type[edge_info[i][j]] == -1
//                           || vect_type[edge_info[i][j]] == 2)
//                 if (  vect_type[edge_info[i][j]] == 3 )
//
//            }
//            //System.out.println("  Nout " + nOut + "  Nin "+ nIn  + "   Nrim " + nRim);
//        //  if (nRim != 4)
//             for (j=0; j< now_nEdge; j++)
//               if ( vect_type[edge_info[i][j]] == 3)
//             {
//                //System.out.println("   to " + edge_info[i][j] + " type " + vect_type[edge_info[i][j]]);
//                ;
//             }
                        //System.out.println(" ");
                    }


                //outerRim.setInfo( nOuterRimPt, order_OuterRimPt, obj);
                //System.out.println("END of error report!!\n\n!!\n\n!!");
                outerRim.nRimPt = -1;
                for (i=1; i<=nNodes; i++)
                    obj.vect_type[i] = vect_type[i];
                return outerRim;
            }
            else
                outerRim.setInfo( nOuterRimPt, order_OuterRimPt, obj);
        } // end of 3rd part

        // 4. densify the object boundary, this will chg the vect, normMat, fac info of the input object
        boolean boundary_densify = true;
        if ( boundary_densify)
        {
            Point3d newPt = new Point3d();
            Vector3d newNormal = new Vector3d();
            for (i=0; i< nFaces; i++)
            {
                int xp1, xp2, xp3, p1=-1, p2=-1, p3=-1;
                xp1 = facInfo[i][0]; xp2 = facInfo[i][1]; xp3 = facInfo[i][2];
                boolean validCondition = false;
                if ( vect_type[xp1] == 3 && vect_type[xp2] == 3 && vect_type[xp3] == 0)
                    validCondition = true;
                else if ( vect_type[xp2] == 3 && vect_type[xp3] == 3 && vect_type[xp1] == 0)
                    validCondition = true;
                else if ( vect_type[xp1] == 3 && vect_type[xp3] == 3 && vect_type[xp2] == 0)
                    validCondition = true;
                if ( ! validCondition)
                    continue;
                // if run till here,this is a face that near boundary

                // rename p1, p2, p3;
                if ( vect_type[xp1] == 3 && vect_type[xp2] == 3)
                { p1 = xp1; p2 = xp2; p3 = xp3;}
                else if ( vect_type[xp1] ==3 && vect_type[xp3] == 3)
                { p1 = xp3; p2 = xp1; p3 = xp2;}
                else if ( vect_type[xp2] ==3 && vect_type[xp3] ==3 )
                { p1 = xp2; p2 = xp3; p3 = xp1;}

                //Adding new vertex, and put it to the end of obj.vect_info
                newPt.add( vect[p1], vect[p2]);
                newPt.scale(0.5);
                newNormal.add( normMat[p1], normMat[p2]);
                newNormal.normalize();

                obj.vect_info[obj.getnVect() +1] = new Point3d( newPt);
                obj.normMat_info[obj.getnVect() +1] = new Vector3d( newNormal);
                obj.setnVect(obj.getnVect() + 1);

                // replace the face, and adding one new face
                obj.getFacInfo()[i][0] = p1; obj.getFacInfo()[i][1] = obj.getnVect(); obj.getFacInfo()[i][2] = p3;

                obj.getFacInfo()[obj.getnFac()][0] = obj.getnVect(); obj.getFacInfo()[obj.getnFac()][1] = p2; obj.getFacInfo()[obj.getnFac()][2] = p3;
                obj.setnFac(obj.getnFac() + 1);
            }
        }
        // copy the vect type to obj.vect_type
        for (i=1; i<=nNodes; i++)
            obj.vect_type[i] = vect_type[i];
        for (i=nNodes+1; i<= obj.getnVect(); i++)
            obj.vect_type[i] = 3;
        //debug
        return outerRim;
    }


    /**
     Function calculate the distance from all vect points on obj1 to the Obj obj2 <BR>
     The reuslts return by a double[] array
     */
    public static double[] distBtwObj( MStickObj4Smooth obj1, MStickObj4Smooth obj2, boolean specialTreat)
    {
        int i;
        double[] distVec = new double[obj1.getnVect() +1];
        for (i=1; i<= obj1.getnVect(); i++)
            distVec[i] = MStickObj4Smooth_staticLib.dist2Object( obj1.vect_info[i], obj2, specialTreat);
        return distVec; // the value range is 0.85 ~ 3.0
    }

    /**
     Function called by distBtwObj in the same class
     This private function calculate the distance from a Point3d to an MAxis Object
     */
    private static double dist2Object( Point3d aimPt, MStickObj4Smooth obj, boolean specialTreat)
    {

//  System.out.println("aim Pt" + aimPt);
//  System.out.println("obj.maxXYZ " + obj.maxXYZ);
//  System.out.println("obj.minXYZ " + obj.minXYZ);
        // 1. quick check AABB of the object

/*
    if ( aimPt.getX() > obj.maxXYZ.getX() || aimPt.getX() < obj.minXYZ.getX() ||
         aimPt.getY() > obj.maxXYZ.getY() || aimPt.getY() < obj.minXYZ.getY() ||
         aimPt.getZ() > obj.maxXYZ.getZ() || aimPt.getZ() < obj.minXYZ.getZ() )
        {
        //System.out.println("fast AABB work");
        return 3.0; // 3.0 means far enough
         }
*/
        //System.out.println("need detailed calc at now = "  );
        // 2. start real calculation
        double dist = 3.0;
        double nowdist = 0.0;
        int i;

        for (i=1; i<= obj.nComponent; i++)
        {
            nowdist = 100.0;
      /*
       if ( aimPt.getX() > obj.comp[i].maxXYZ.getX() || aimPt.getX() < obj.comp[i].minXYZ.getX() ||
            aimPt.getY() > obj.comp[i].maxXYZ.getY() || aimPt.getY() < obj.comp[i].minXYZ.getY() ||
            aimPt.getZ() > obj.comp[i].maxXYZ.getZ() || aimPt.getZ() < obj.comp[i].minXYZ.getZ() )
        nowdist = 3.0; // far from this particular tube
      */
            if ( nowdist != 3.0)
            {
                //System.out.println("    need EVEN detailed calc at now = "  );
                nowdist = MStickObj4Smooth_staticLib.dist2Tube( aimPt, obj.comp[i], specialTreat);
            }
            if ( nowdist < dist)
                dist = nowdist;
            if (dist < 0.85 ) //which is small enough for our purpose, WELL, we might remove this line, think later
                return 0.85;
        }
        return dist;
    }

    /**
     Function called by distBtwObj in the same class
     This private function calculate the distance from a Point3d to a single MAxis Tube
     */
    private static double dist2Tube( Point3d nowPt, TubeComp tube, boolean specialTreat)
    {

        int sampleStep = tube.getMaxStep();
        //System.out.println("sample step = " + sampleStep);
        specialTreat = false;
        int i;
        double dist = 3.0, nowdist;
        int start = 1;
        int endNdx = sampleStep;
        if (specialTreat == true)
        {
            start = 1;
            endNdx = sampleStep -10;
        }
        for (i=start; i<= endNdx; i++)
        //for (i=3; i<=sampleStep-2 ; i++) // ignore the first several tip a very tricky way to make a thing work (about N71's posthoc)
        {
            double denom = tube.getRadiusAcross()[i];
            if (specialTreat)
                denom = denom * 0.9;
            //nowdist = ( nowPt.distance( tube.mAxisInfo.mPts[i]) ) / tube.radiusAcross[i];
            nowdist = ( nowPt.distance( tube.getmAxisInfo().getmPts()[i]) ) / denom;

            if ( nowdist < dist)
                dist = nowdist;
            if (dist < 0.85) // good enough value
                return 0.85;

        }
        return dist;
    }
}