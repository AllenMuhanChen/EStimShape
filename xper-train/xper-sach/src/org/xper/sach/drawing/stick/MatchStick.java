
package org.xper.sach.drawing.stick;

import java.io.BufferedReader;
import java.io.FileReader;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.IntBuffer;
import java.util.ArrayList;
import java.util.List;

import javax.media.j3d.Transform3D;
import javax.vecmath.AxisAngle4d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;

import org.jtransforms.fft.DoubleFFT_2D;
import org.lwjgl.opengl.GL11;
import org.lwjgl.util.glu.GLU;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.sach.drawing.splines.MyPoint;
import org.xper.sach.drawing.stick.mathLib.stickMath_lib;
import org.xper.sach.drawing.stimuli.TextureType;
import org.xper.sach.util.ComplexMatrix;

// import shapeGen.ShapeSpec;
// import DataAnalysis.MAxisInfoDescriptor;
// import DataAnalysis.divideTubeComp;
public class MatchStick
{
    // the final magificatin factor for the vect
    final double scaleForMAxisShape  = 1.0;

    public MatchStick tempStick ;
    public MatchStick parentStick;
    public int showMode = 1;
    public double[] finalRotation;
    public Point3d finalShiftinDepth;
    public int nComponent;

    ArrayList<Coordinates2D> texSpec;
    ArrayList<Point3d> texFaceSpec;

    //variable describe the MStick
    public TubeComp[] comp = new TubeComp[9];
    public int nEndPt;
    public int nJuncPt;
    public EndPt_struct[] endPt = new EndPt_struct[50]; // 30 is just an arbitrary large enough number
    public JuncPt_struct[] JuncPt = new JuncPt_struct[50];
    public MStickObj4Smooth obj1;
    private boolean[] LeafBranch = new boolean[10];

    private final double[] PARAM_nCompDist = {0.0,0.2, 0.6, 1.0, 0.0, 0.0, 0.0, 0.0};

    private final double PROB_addToEndorJunc = 1; // 60% add to end or junction pt, 40% to the branch
    private final double PROB_addToEnd_notJunc = 0.3; // when "addtoEndorJunc", 50% add to end, 50% add to junc
                      // however, if # of junc Pt == 0, always add to End
    private final double PROB_addTiptoBranch = 0; // when "add new component to the branch is true"
    private final double ChangeRotationVolatileRate = 0;
                      // the prob. of chg the final rot angle after a GA mutate
    private final double TangentSaveZone = Math.PI / 6.0;
    // declaration of the class

	//temp, should remove later
    public int nowCenterTube;

    double externalSizeParam = 1;
    MyPoint xyPosition = new MyPoint(0, 0);
    boolean doCenterShape = false;
    boolean alreadyCentered = false;
    boolean alreadyClouded = false;
    boolean doLowPass = true;
    boolean alreadyLowPassed = false;

    int viewport = 0;
    int frameNum = 0;

    private boolean doClouds;
    private Point3d[] boundingBox;
    ByteBuffer pixelsToWrite;
    int minX, minY, nPixX, nPixY;
    boolean isScreenInverted = false;

    public MatchStick() //constructor
    {
    }

    /**
        clean the old storage of information
    */
    private void cleanData() {
        showMode = 1;
        nComponent = 0;
        nEndPt = 0;
        nJuncPt = 0;
    }
        /**
        genMatchStick with random # of components
        */

    /**
        copy the whole structure
    */
    public void copyFrom(MatchStick in)
    {
        int i;

        this.showMode = in.showMode;
        this.nComponent = in.nComponent;
//      if (in.parentStick == null)
//          this.parentStick = null;
//      else
//          this.parentStick.copyFrom(in.parentStick);
        for (i=1; i<=nComponent; i++)
        {
            this.comp[i] = new TubeComp();
            this.comp[i].copyFrom(in.comp[i]);
        }
        this.nEndPt = in.nEndPt;
        for (i=1; i<=nEndPt; i++)
        {
            this.endPt[i] = new EndPt_struct();
            this.endPt[i].copyFrom(in.endPt[i]);
        }
        this.nJuncPt = in.nJuncPt;
        for (i=1; i<=nJuncPt; i++)
        {
            this.JuncPt[i] = new JuncPt_struct();
            this.JuncPt[i].copyFrom(in.JuncPt[i]);
        }
        this.obj1 = in.obj1; // don't know if this object copy is okay or not, be careful
                     // probably fine, but be careful!!

        for (i=1; i<=nComponent; i++)
            this.LeafBranch[i] = in.LeafBranch[i];
    }

    /**
     *   Function that manually set first component
     */
    private void createFirstCompManually(Point3d pos, Vector3d tangent, int alignedPt,
                                double rad, double arcLen, double devAngle)
    {
        MAxisArc nowArc = new MAxisArc();
        nowArc.genArc(rad, arcLen);
        nowArc.transRotMAxis(alignedPt, pos, alignedPt, tangent, devAngle);

        comp[1].initSet( nowArc, false, 0); // the MAxisInfo, and the branchUsed
        //update the endPt and JuncPt information
        this.endPt[1] = new EndPt_struct(1, 1, comp[1].mAxisInfo.mPts[1], comp[1].mAxisInfo.mTangent[1] , 100.0);
        this.endPt[2] = new EndPt_struct(1, 51, comp[1].mAxisInfo.mPts[51], comp[1].mAxisInfo.mTangent[51], 100.0);
        this.nEndPt = 2;
        this.nJuncPt = 0;
    }
    /**
     *   manually adding new MStick with specific type, with specific instruction
     */


    private boolean Add_MStickManually(int nowComp, int type, double in_rad, double in_arcLen,
                    int in_endPtLabel, int in_JuncPtLabel,int in_tubeToAttach,
                    Vector3d in_tangent, double in_devAngle)
    {
        //July 10th, the different thing here from Add_MStick is that:
        // We can manually input the specific orientation and arcLen, rad of the new tube
        // Add new component to a existing partial MStick
        // 4 types of addition are possible , specified by type
        // 1. type == 1: E2E connection
        // 2. type == 2: E2J connection
        // 3. type == 3: E2B connection
        // 4. type == 4: B2E connection

                //shared variable declaration
        boolean showDebug = false;
        //final double TangentSaveZone = Math.PI / 4.0;
        int i;

        if (showDebug)
        {
            System.out.println("In AddMStickManually: nowComp " + nowComp + " type: " + type);
            System.out.println("now nEndPt " + nEndPt + " , and nJuncPt " + nJuncPt);
        }

        // generate a new Arc with specific, in_rad, in_arcLen
        MAxisArc nowArc = new MAxisArc();
        nowArc.genArc(in_rad, in_arcLen);

        if (type == 1) // Adding the new Comp end-to-end
        {
           // 1. pick an endPt
            int nowPtNdx;
            nowPtNdx = in_endPtLabel; // a input parameter

           // 2. transRot the nowArc to the correct configuration
            int alignedPt = 1;
            Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
            Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
            Vector3d finalTangent = new Vector3d(in_tangent);

            if ( oriTangent.angle(finalTangent) < TangentSaveZone )
            {   // angle btw the two tangent vector
                System.out.println("The angle btw tangent is too tight in type 1 add!");
            }

            double devAngle = in_devAngle;
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);

            // 3. update the EndPT to JuncPt
            nJuncPt++;
            int[] compList = { endPt[nowPtNdx].comp, nowComp};
            int[] uNdxList = { endPt[nowPtNdx].uNdx, 1};
            Vector3d[] tangentList = { oriTangent, finalTangent};
            this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, endPt[nowPtNdx].rad);
            comp[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

                // 2.5 call the function to check if this new arc is valid
            /*
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nJuncPt] = null;
                nJuncPt--;
                return false;
            }
            */
            // 4. generate new endPt
            this.endPt[nowPtNdx].setValue(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
            // 5. save this new Comp

        }
        else if (type == 2) // end to Junction connection
        {
            //1. pick a Junction Pt

            if (this.nJuncPt == 0)
            {
                System.out.println("ERROR, should not choose type 2 addition when nJuncPt = 0");
                return false;
            }
            int nowPtNdx = in_JuncPtLabel;
            //2. transRot the newComp
            int alignedPt = 1;
            Point3d finalPos = new Point3d(JuncPt[nowPtNdx].pos);
            Vector3d finalTangent = new Vector3d(in_tangent);


                boolean flag = true;
                for (i=1; i<= JuncPt[nowPtNdx].nTangent; i++)
                {
                    if ( finalTangent.angle( JuncPt[nowPtNdx].tangent[i]) <= TangentSaveZone)
                        flag = false;
                }
                if (flag == false) // i.e. all the tangent at this junction is ok for this new tangent
                {
                    //return false;
                    System.out.println("the tangent too close in type 2 addition");
                }


            double devAngle = in_devAngle;
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);

            //3. update the JuncPt & endPt info and add the new Comp
            JuncPt_struct old_JuncInfo = new JuncPt_struct();
            old_JuncInfo.copyFrom(JuncPt[nowPtNdx]);
            this.JuncPt[nowPtNdx].addComp(nowComp, 1, nowArc.mTangent[1]);
            comp[nowComp].initSet(nowArc, false, 2);
                // 2.5 call the function to check if this new arc is valid
            /*
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nowPtNdx].copyFrom(old_JuncInfo);
                return false;
            }
             */
            nEndPt++;
            this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);

        }
        else if (type == 3) //end-to-branch connection
        {
             // 1. select a existing comp, with free branch
            int pickedComp = in_tubeToAttach;

            if ( comp[pickedComp].branchUsed == true)
            {
                System.out.println("the branch of this tube is already used in type3 add");
            }
             // 2. transrot the newComp
            int alignedPt = 1;
            int nowUNdx = comp[pickedComp].mAxisInfo.branchPt;
            Point3d finalPos = new Point3d( comp[pickedComp].mAxisInfo.mPts[nowUNdx]);
            Vector3d oriTangent1 = new Vector3d( comp[pickedComp].mAxisInfo.mTangent[nowUNdx]);
            Vector3d oriTangent2 = new Vector3d();
            Vector3d finalTangent = new Vector3d(in_tangent);
            oriTangent2.negate(oriTangent1);

            if ( finalTangent.angle(oriTangent1) < TangentSaveZone ||
                     finalTangent.angle(oriTangent2) < TangentSaveZone    )
            {
                    System.out.println("tangent too near in type 3 add tube");
                    //return false;
            }

            double devAngle = in_devAngle;
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
             // 2.5 check if newComp valid
             // 3. update the JuncPt & endPt info
            nJuncPt++;
            int[] compList = { pickedComp, nowComp};
            int[] uNdxList = { nowUNdx, 1};
            Vector3d[] tangentList = { oriTangent1, oriTangent2, finalTangent};
            int[] ownerList = { pickedComp, pickedComp, nowComp};
            double rad = 100.0;
            rad = comp[pickedComp].radInfo[1][1]; // if it is existing tube, then there will be a value
                //otherwise, it should be initial value of 100.0
            this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);
            //JuncPt[nJuncPt].showInfo();
                // 2.5 call the function to check if this new arc is valid
            comp[nowComp].initSet(nowArc, false, 3);
            /*
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nJuncPt] = null;
                nJuncPt--;
                System.out.println("type 3 addition fail");
                return false;
            }
            */
            nEndPt++;
            this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
            comp[pickedComp].branchUsed = true;


        }
        else if (type == 4) // add branch to the existing EndPt
        {
            // 1. pick an EndPt

            int nowPtNdx = in_endPtLabel;

            // 2. transRot newComp
            int nowUNdx = nowArc.branchPt;
            int alignedPt = nowUNdx;
            Vector3d rev_tangent = new Vector3d();
            Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
            Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
            Vector3d finalTangent = new Vector3d(in_tangent);

            rev_tangent.negate(finalTangent);
            if ( oriTangent.angle(finalTangent) < TangentSaveZone ||
                     oriTangent.angle(rev_tangent) < TangentSaveZone    )
            {
                System.out.println("tangent too nearby in add tube type 4");
                //return false;
            }

            double devAngle = in_devAngle;
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
            // 2.5 check Nearby Situation
            // 3. update JuncPt & endPt info
            nJuncPt++;
            int[] compList = { endPt[nowPtNdx].comp, nowComp};
            int[] uNdxList = { endPt[nowPtNdx].uNdx, nowUNdx};
            Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
            int[] ownerList = {endPt[nowPtNdx].comp, nowComp, nowComp};
            double rad;
            rad = endPt[nowPtNdx].rad;
            this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

            // 2.5 call the function to check if this new arc is valid
            comp[nowComp].initSet(nowArc, true, 4);
            /*
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nJuncPt] = null;
                nJuncPt--;
                return false;
             }
             */
            // 4. generate 2 new endPt
            this.endPt[nowPtNdx].setValue(nowComp, 1, nowArc.mPts[1], nowArc.mTangent[1], 100.0);
            nEndPt++;
            this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);

        }

        if ( showDebug)
            System.out.println("\n end of add tube func successfully \n");
        return true;
        // call the check function to see if the newly added component violate the skeleton nearby safety zone.
    }

    /**
     *   Assign the radius value manually
     */

    private void RadiusAssignManually(double[] JuncPt_radList, double[] endPt_radList,
                        double[] midPt_radList)
    {

        double rMin, rMax;
        double nowRad, u_value, tempX;


        //The goal here is to assign the radius value for each tube
        //I think good way is to follow, assign at JuncPt, endPt, and then middle Pt

        int i, j;
            // 0. initialize to negative value
        for (i= 1; i<=nComponent; i++)
        {
          comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
        }
            // 1. assign at JuncPt
        for (i=1; i<=nJuncPt; i++)
        {
          if ( JuncPt[i].rad == 100.0) // a whole new JuncPt
          {
             rMin = -10.0; rMax = 100000.0;
                 int nRelated_comp = JuncPt[i].nComp;
                 for (j = 1 ; j <= nRelated_comp; j++)
             {
                    rMin = Math.max( rMin, comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 10.0);
                    tempX = Math.min( 0.5 *comp[JuncPt[i].comp[j]].mAxisInfo.rad,
                 comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 4.0);
                    rMax = Math.min( rMax, tempX);
             }
                 nowRad = JuncPt_radList[i];
                 System.out.println("JuncPt" + i +" "+ "min max now are: "+
                         rMin + " " + rMax + " " + nowRad );
                 if ( nowRad > rMax || nowRad < rMin)
                     System.out.println("   rad NOT in legal Range!");

             JuncPt[i].rad = nowRad;

             for (j = 1 ; j <= nRelated_comp ; j++)
             {
                      u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                      if ( Math.abs( u_value - 0.0) < 0.0001)
                      {
                        comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                        comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
                      }
                      else if ( Math.abs(u_value - 1.0) < 0.0001)
                      {
                          comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                          comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
                      }
                      else // middle u value
                      {
                          comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                          comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
                      }
              }
           }
        } // loop nJuncPt

        // 2. assign at endPt
        for ( i = 1 ;  i <= nEndPt ; i++)
        {

            int nowComp = endPt[i].comp;
            u_value = ((double)endPt[i].uNdx -1.0 ) / (51.0 -1.0);

            //rMin = mStick.comp(nowComp).arcLen / 10.0;
            rMin = 0.00001; // as small as you like
            rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 4.0, 0.5 * comp[nowComp].mAxisInfo.rad);

            // select a value btw rMin and rMax
            nowRad = endPt_radList[i];

            System.out.println("endPt" + i +" "+ "min max now are: "+
                 rMin + " " + rMax + " " + nowRad );
            if ( nowRad > rMax || nowRad < rMin)
                System.out.println("    rad NOT in legal Range!");

            endPt[i].rad = nowRad;

            if ( Math.abs( u_value - 0.0) < 0.0001)
            {
                comp[nowComp].radInfo[0][0] = 0.0;
                comp[nowComp].radInfo[0][1] = nowRad;
            }
            else if (Math.abs(u_value - 1.0) < 0.0001)
            {
                comp[nowComp].radInfo[2][0] = 1.0;
                comp[nowComp].radInfo[2][1] = nowRad;
            }
            else // middle u value
                 System.out.println( "error in endPt radius assignment");

        }

        // 3. other middle Pt
          for ( i = 1 ; i <= nComponent ; i++)
              if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
            {
                int branchPt = comp[i].mAxisInfo.branchPt;
                u_value = ((double)branchPt-1.0) / (51.0 -1.0);

                rMin = comp[i].mAxisInfo.arcLen / 10.0;
                rMax = Math.min(comp[i].mAxisInfo.arcLen / 4.0, 0.5 * comp[i].mAxisInfo.rad);
                nowRad = midPt_radList[i];

                System.out.println("midPt" + i +" "+ "min max now are: "+
                             rMin + " " + rMax + " " + nowRad );

                if ( nowRad > rMax || nowRad < rMin)
                    System.out.println("    rad NOT in legal Range!");

                comp[i].radInfo[1][0] = u_value;
                comp[i].radInfo[1][1] = nowRad;
            }

    }

    /**
     *    Function that we use to manually determine which stick to add, to posit
     */
    public void genMatchStickManually()
    {
        int nComp;
        int i;

        this.cleanData();

        nComp = 8;
        this.nComponent = nComp;

        for (i=1; i<=nComp; i++)
                comp[i] = new TubeComp();

        // 1. first component
        {
          Point3d finalPos = new Point3d(0,0,0); //always put at origin;
          Vector3d finalTangent = new Vector3d(1,0,0);
          int alignedPt = 26; // make it always the center of the mAxis curve
          double rad = 10000.0;
          double arcLen = 3.5;
          double devAngle = 0;

          createFirstCompManually(finalPos, finalTangent, alignedPt, rad, arcLen, devAngle);
        }
        /*
         *   Notice: The range of parameters should be
         *   rad: 1.0~30.0 or 100000 for str8
         *   ArcLen: 2.0 ~ Min( PI * rad, 5.0)
         *   in_endPtLabel is useful for type 1 & 4 addition
         *   in_JuncPtLabel is useful for type 2 addition, to junciton
         *   in_tubeToAttach is useful for type 3 addition to a branchPt
         *   devAngle = 0 ~ 2pi
         */

        // 2.2 adding comp2
        {
            int nowComp = 2;
            int type = 1; // end-to-end
            double rad = 10000.0, arcLen = 3.4;
            int endPtLabel = 2, JuncPtLabel=-1, tubeToAttach = -1;
            double devAngle = 0.0;
            Vector3d tangent = new Vector3d(0.5,2,0);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 2.3, adding comp 3
        {
            int nowComp = 3;
            int type = 1; // end-to-end
            double rad = 100000.0, arcLen = 3.0;
            int endPtLabel = 1, JuncPtLabel=-1, tubeToAttach = -1;
            double devAngle = 0.0;
            Vector3d tangent = new Vector3d(0.1,-0.8, 0.2);
            //Vector3d tangent = new Vector3d(-0.3, -0.8, 1);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 2.4, adding comp 4
        {
            int nowComp = 4;
            int type = 2; // end-to-end
            double rad = 100000.0, arcLen = 3.0;
            int endPtLabel = -1, JuncPtLabel= 2, tubeToAttach = -1;
            double devAngle = 0.0;
            Vector3d tangent = new Vector3d(-0.3,-0.8, -0.2);
            //Vector3d tangent = new Vector3d(0.3, -0.8, -1);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 2.5, adding comp 5
        {
            int nowComp = 5;
            int type = 2; // end-to-junc
            double rad = 100000.0, arcLen = 3.0;
            int endPtLabel = -1, JuncPtLabel= 1, tubeToAttach = -1;
            double devAngle = 0.0;
            Vector3d tangent = new Vector3d(0.2,-0.8, 0.2);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 2.6, adding comp 6
        {
            int nowComp = 6;
            int type = 2; // end-to-junc
            double rad = 100000.0, arcLen = 3.0;
            int endPtLabel = -1, JuncPtLabel= 1, tubeToAttach = -1;
            double devAngle = 0.0;
            Vector3d tangent = new Vector3d(-0.3,-1.8, -0.2);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 2.8, adding comp 7, tail
        {
            int nowComp = 7;
            int type = 2; // end-to-junc
            double rad = 1.3, arcLen = 2.7;
            int endPtLabel = -1, JuncPtLabel= 2, tubeToAttach = -1;
            double devAngle = Math.PI;
            Vector3d tangent = new Vector3d(-1, 0.5, 0);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 2.8, adding comp 7, head
        {
            int nowComp = 8;
            int type = 1; // end-to-end
            double rad = 10000.0, arcLen = 1.7;
            int endPtLabel = 2, JuncPtLabel= 0, tubeToAttach = -1;
            double devAngle = 0;
            Vector3d tangent = new Vector3d(1.7, -2.5, 0);
            tangent.normalize();

            Add_MStickManually(nowComp, type, rad, arcLen, endPtLabel, JuncPtLabel,
                tubeToAttach, tangent, devAngle);
        }

        // 3. apply the radius value and calculate the skin
        //Assign the radius value
        double[] JuncPtR = new double[nJuncPt+1];
        double[] endPtR = new double[nEndPt+1];
        double[] midPtR = new double[nComponent+1];

        { // just assign by hand
            JuncPtR[1] = 1.0;
            JuncPtR[2] = 1.0;
            JuncPtR[3] = 0.4;
            //JuncPt_radList[2] = 1.0;

            endPtR[1] = 0.45;
            endPtR[2] = 0.65;
            endPtR[3] = 0.45;
            endPtR[4] = 0.45;
            endPtR[5] = 0.45;
            endPtR[6] = 0.03;

            midPtR[1] = 1.2;
            midPtR[2] = 0.43;
            midPtR[3] = 0.45;
            midPtR[4] = 0.45;
            midPtR[5] = 0.45;
            midPtR[6] = 0.45;
            midPtR[7] = 0.45;
            midPtR[8] = 0.45;

        }
        this.RadiusAssignManually(JuncPtR, endPtR, midPtR);
        // 4. Apply the radius value onto each component

        boolean validShape = true;
        for (i=1; i<=nComponent; i++)
        {
            if( this.comp[i].RadApplied_Factory() == false) // a fail application
            {
               validShape = false;
               System.out.println("skin generation fail in manually application!");
            }
        }

        // 5. check if the final shape is not working ( collide after skin application)

        if ( this.validMStickSize() ==  false)
        {
            validShape = false;
            System.out.println("\n FAIL the MStick size check in manually gen\n");
        }
        /*
        if ( this.finalTubeCollisionCheck() == true)
        {
            validShape = false;
            System.out.println("\n FAIL the final Tube collsion Check in maually gen\n");
        }
        */

        if ( validShape == false)
        {
            System.out.println("not successful generation, plz check");
            return;
        }


        this.finalRotation = new double[3];
        finalRotation[0] = 0.0;
        finalRotation[1] = 0.0;
        finalRotation[2] = 0.0;

        //this.finalRotateAllPoints(finalRotation[0], finalRotation[1], finalRotation[2]);


        boolean res = this.smoothizeMStick();
        if ( res == false) // success to smooth
        {
            System.out.println("the manual input parameters fail!");
        }
       this.parentStick = new MatchStick();


       //write the result into spec and then write into a file
       MStickSpec g = new MStickSpec();
       g.setMStickInfo(this);
//       g.writeInfo2File();

//       ShapeSpec nowSpec =new ShapeSpec();
//       nowSpec.setMAxisSpec(this);
//       nowSpec.writeInfo2File("./sample/nowOut.xml");

    }

    /**
     *    genMatchStickFrom spec data
     *    Read in a spec structure, and dump those info into this MAxis structure
     */
    public void genMatchStickFromShapeSpec( MStickSpec inSpec)
    {
        // i can't see how inSpec is changed by this function
        //but it seems to be the case........
        this.cleanData();

        // 1. general info
        int nComp = inSpec.mAxis.nComponent;
        this.nComponent = nComp;
        int i, j, k;

        // 2. tube info

        for (i=1; i<=nComp; i++)
        {
            //debug
            //System.out.println("comp " + i + " : ");
            comp[i] = new TubeComp();
            comp[i].branchUsed = inSpec.mAxis.Tube[i].branchUsed;
            comp[i].connectType = inSpec.mAxis.Tube[i].connectType;
            for (j=0; j<3; j++)
                for (k=0; k<2; k++)
                {
                  comp[i].radInfo[j][k] = inSpec.mAxis.Tube[i].radInfo[j][k];
                 // System.out.print(comp[i].radInfo[j][k] + " " );
                }
            //System.out.println(" " );
            comp[i].mAxisInfo.arcLen = inSpec.mAxis.Tube[i].mAxis_arcLen;
            comp[i].mAxisInfo.rad = inSpec.mAxis.Tube[i].mAxis_rad;
            comp[i].mAxisInfo.branchPt = inSpec.mAxis.Tube[i].mAxis_branchPt;
            //System.out.println("branchPt " + comp[i].mAxisInfo.branchPt);

            comp[i].mAxisInfo.transRotHis_alignedPt = inSpec.mAxis.Tube[i].transRotHis_alignedPt;
            comp[i].mAxisInfo.transRotHis_rotCenter = inSpec.mAxis.Tube[i].transRotHis_rotCenter;
            comp[i].mAxisInfo.transRotHis_finalPos =// inSpec.mAxis.Tube[i].transRotHis_finalPos;
                new Point3d( inSpec.mAxis.Tube[i].transRotHis_finalPos);
            comp[i].mAxisInfo.transRotHis_finalTangent =// inSpec.mAxis.Tube[i].transRotHis_finalTangent;
                new Vector3d( inSpec.mAxis.Tube[i].transRotHis_finalTangent);
            comp[i].mAxisInfo.transRotHis_devAngle = inSpec.mAxis.Tube[i].transRotHis_devAngle;

        }

        // 3. endPt info
        this.nEndPt = inSpec.mAxis.nEndPt;

        for (i=1; i<=nEndPt; i++)
        {
            this.endPt[i] = new EndPt_struct();
            endPt[i].comp = inSpec.mAxis.EndPt[i].comp;
            endPt[i].uNdx = inSpec.mAxis.EndPt[i].uNdx;
            endPt[i].pos = new Point3d( inSpec.mAxis.EndPt[i].pos);
            endPt[i].tangent = new Vector3d( inSpec.mAxis.EndPt[i].tangent);
            endPt[i].rad = inSpec.mAxis.EndPt[i].rad;
        }

        // 4. juncPt info
        this.nJuncPt = inSpec.mAxis.nJuncPt;
        for (i=1; i<=nJuncPt; i++)
        {
            this.JuncPt[i] = new JuncPt_struct();
            JuncPt[i].nComp = inSpec.mAxis.JuncPt[i].nComp;
            JuncPt[i].nTangent = inSpec.mAxis.JuncPt[i].nTangent;
            JuncPt[i].rad = inSpec.mAxis.JuncPt[i].rad;
            JuncPt[i].pos = new Point3d(inSpec.mAxis.JuncPt[i].pos);

            for (j=1; j<= JuncPt[i].nComp; j++)
            {
                JuncPt[i].comp[j] = inSpec.mAxis.JuncPt[i].comp[j];
                JuncPt[i].uNdx[j] = inSpec.mAxis.JuncPt[i].uNdx[j];
            }
            for (j=1; j<= JuncPt[i].nTangent; j++)
            {
                JuncPt[i].tangent[j] = new Vector3d( inSpec.mAxis.JuncPt[i].tangent[j]);
                JuncPt[i].tangentOwner[j] = inSpec.mAxis.JuncPt[i].tangentOwner[j];
            }

        }

        // May 22nd, we find after GA
        // sometimes the tangent will be wrong direction
        // (while we assume the tangent in JuncPt, EndPt are correct
        // In this case we want to do the modifcation!
        // This might not be the ultimate solving way
        // but, just do it for now

        for (i=1; i<=nComp; i++)
        {
            comp[i].mAxisInfo.genArc( comp[i].mAxisInfo.rad, comp[i].mAxisInfo.arcLen);
            comp[i].mAxisInfo.transRotMAxis(comp[i].mAxisInfo.transRotHis_alignedPt,
                comp[i].mAxisInfo.transRotHis_finalPos,
                comp[i].mAxisInfo.transRotHis_rotCenter,
                comp[i].mAxisInfo.transRotHis_finalTangent,
                comp[i].mAxisInfo.transRotHis_devAngle);
            comp[i].RadApplied_Factory(); // since we didn't save these info


        }



        // 5. final rotation info
        this.finalRotation = new double[3];
        for (i=0; i<3; i++)
            this.finalRotation[i] = inSpec.mAxis.finalRotation[i];

        // 6. calculate the smooth vect and fac info

         // 2008, Nov, we should not do a rotation again here, since the original ShapeSpec info should already be rotated
         // again, or we should do it!
        //this.finalRotateAllPoints( finalRotation[0], finalRotation[1], finalRotation[2]);

        boolean res = this.smoothizeMStick();
        if ( res == false) // success to smooth
        {
            System.out.println("Fail to smooth while using info from a shapeSpec");
            System.out.println("THIS SHOULD NOT HAPPEN1");
            return;
        }

        // ***** IMPORTANT
        // temp, Feb 15th 2011
        // a temporary work away for the thin tube in post-hoc
        // we want to have the correct smooth of the matchStick type shape
        // in that case, we don't worry if the original mesh and now mesh is incompatible
        // So, we will jus activate the following 3 lines. which igonroe all the below codes
//        int a = 3;
        //if (a==3)
        //  return;


        //May 22nd
        // we found in our old generating system
        // the 'finalTangent' is sometimes at 'wrong direction'
        // At here we want to check the similarity ( reproducibility)
        // of our new synthesized shape & original vertex distance
        if ( res == true)
        {
        	return;
//            if ( inSpec.getNVect() < 10) // this might happen, not sure
//            {
////                System.out.println("no old smooth vertex info yet");
//                return;
//            }
//            Point3d[] oriVecList = inSpec.getVectInfo();
//            double vect_dist = 0.0;
//            int nVect1 = this.obj1.nVect;
//            int nVect2 = inSpec.getNVect();
//            System.out.println("      vec # check " + nVect1 + " " + nVect2);
//            if ( nVect1 != nVect2)
//            {
//                res = false;
//                System.out.println("            vec # unmatch");
//            }
//            if ( res == true)
//            {
//                for (i= 1; i<= this.obj1.nVect; i++)
//                {
//                    Point3d p1 = new Point3d(obj1.vect_info[i]);
//                    Point3d p2 = oriVecList[i];
//                    vect_dist += p1.distance(p2);
//                }
//                System.out.println("            total vect dist is :" + vect_dist);
//                if ( vect_dist > 5.0)
//                    res = false;
//            }
        }

        boolean tryFlip = true;
        // step1. try to flip the tangent dir of single tube
        if ( res == false)
        {

              System.out.println("we should try to switch the tangent dir");
              if ( tryFlip == false)
                    return;
             // this.nComponent = -1;
              int tryComp;
             for (tryComp= 1; tryComp <=nComp; tryComp++)
             {
                    //key line  ---> flip the tangent dir
                    System.out.println("try to flip comp " + tryComp);
                    comp[tryComp].mAxisInfo.transRotHis_finalTangent.negate();

                    for (i=1; i<=nComp; i++)
                    {
                        comp[i].mAxisInfo.genArc( comp[i].mAxisInfo.rad, comp[i].mAxisInfo.arcLen);
                        comp[i].mAxisInfo.transRotMAxis(comp[i].mAxisInfo.transRotHis_alignedPt,
                        comp[i].mAxisInfo.transRotHis_finalPos,
                        comp[i].mAxisInfo.transRotHis_rotCenter,
                        comp[i].mAxisInfo.transRotHis_finalTangent,
                        comp[i].mAxisInfo.transRotHis_devAngle);
                        comp[i].RadApplied_Factory(); // since we didn't save these info
                    }

                    res = this.smoothizeMStick();
                    if ( res == false) // success to smooth
                    {
                        System.out.println("Fail to smooth while using info from a shapeSpec");
                        System.out.println("THIS SHOULD NOT HAPPEN2");
                    }


                    if ( res == true)
                    {
                        Point3d[] oriVecList = inSpec.getVectInfo();
                        double vect_dist = 0.0;
                        int nVect1 = this.obj1.nVect;
                        int nVect2 = inSpec.getNVect();
                        System.out.println("vec # check " + nVect1 + " " + nVect2);
                        if ( nVect1 != nVect2)
                        {
                            res = false;
                            System.out.println("vec # unmatch");
                        }
                        if ( res == true)
                        {
                            for (i= 1; i<= this.obj1.nVect; i++)
                            {
                                Point3d p1 = new Point3d(obj1.vect_info[i]);
                                Point3d p2 = oriVecList[i];
                                vect_dist += p1.distance(p2);
                            }
                            System.out.println("total vect dist is :" + vect_dist);
                            if ( vect_dist > 5.0)
                                res = false;
                        }
                    }

                    //debug, remember to remove it //feb 15 2011

                    if ( res == true) // great this flip work
                    {
                        System.out.println("flip " + tryComp + " work");
                        break;
                    }
                    else                //flip back
                            comp[tryComp].mAxisInfo.transRotHis_finalTangent.negate();

             } // for loop
        }

        if ( res == false)
        {
            System.out.println("try flip all final tangent one-by-one, no work!");
            System.out.println("check this shape out!!!");
            // July 23rd 2009
            //debug, may need to remove later
                //  this.nComponent = -1;

        }
        // step2. try to change the finalTangent dir to what we have in JuncPt/EndPt
        boolean JuncAssignWork = false;
        if ( res == false)
        {

              System.out.println("try to use tangent Info in Junc/End Pt");

              int tryComp;
              for (tryComp= 1; tryComp <=nComp; tryComp++)
              {
                  // collect all the possible tangent into an array
                  Vector3d[] candidate = new Vector3d[20];
                  for (i=0; i<20; i++) candidate[i] = new Vector3d();
                  int nCandidate = 0;
                  for (i=1; i<= this.nEndPt; i++)
                  {
                      if (this.endPt[i].comp == tryComp)
                      {
                          candidate[nCandidate].set( endPt[i].tangent);
                          candidate[nCandidate+1].set( endPt[i].tangent);
                          candidate[nCandidate+1].negate();
                          nCandidate +=2;
                      }
                  }

                  for (i=1; i<= this.nJuncPt; i++)
                  {
                      for (j=1; j<= JuncPt[i].nTangent; j++)
                          if  (JuncPt[i].tangentOwner[j] == tryComp)
                      {
                          candidate[nCandidate].set( JuncPt[i].tangent[j]);
                          candidate[nCandidate+1].set( JuncPt[i].tangent[j]);
                          candidate[nCandidate+1].negate();
                          nCandidate +=2;

                      }
                  }

                  for (k=0; k< nCandidate; k++)
                  {
                      //key line  ---> flip the tangent dir
                      System.out.println("try to assign comp " + tryComp + " with " + k + " candidate");
                      Vector3d oriVec = new Vector3d(comp[tryComp].mAxisInfo.transRotHis_finalTangent);
                      comp[tryComp].mAxisInfo.transRotHis_finalTangent.set(candidate[k]);
                      //comp[tryComp].mAxisInfo.transRotHis_finalTangent.negate();
                      //if (tryComp > 1) //flip back last one
                      //comp[tryComp-1].mAxisInfo.transRotHis_finalTangent.negate();

                      for (i=1; i<=nComp; i++)
                      {
                          comp[i].mAxisInfo.genArc( comp[i].mAxisInfo.rad, comp[i].mAxisInfo.arcLen);
                          comp[i].mAxisInfo.transRotMAxis(comp[i].mAxisInfo.transRotHis_alignedPt,
                          comp[i].mAxisInfo.transRotHis_finalPos,
                          comp[i].mAxisInfo.transRotHis_rotCenter,
                          comp[i].mAxisInfo.transRotHis_finalTangent,
                          comp[i].mAxisInfo.transRotHis_devAngle);
                          comp[i].RadApplied_Factory(); // since we didn't save these info
                        }

                      res = this.smoothizeMStick();
                      if ( res == false) // success to smooth
                      {
                          System.out.println("Fail to smooth while using info from a shapeSpec");
                          System.out.println("THIS SHOULD NOT HAPPEN3");
                      }

                      if ( res == true)
                      {
                          Point3d[] oriVecList = inSpec.getVectInfo();
                          double vect_dist = 0.0;
                          int nVect1 = this.obj1.nVect;
                          int nVect2 = inSpec.getNVect();
                          System.out.println("vec # check " + nVect1 + " " + nVect2);
                          if ( nVect1 != nVect2)
                          {
                              res = false;
                              System.out.println("vec # unmatch");
                          }
                          if ( res == true)
                          {
                            for (i= 1; i<= this.obj1.nVect; i++)
                            {
                                Point3d p1 = new Point3d(obj1.vect_info[i]);
                                Point3d p2 = oriVecList[i];
                                vect_dist += p1.distance(p2);
                            }
                            System.out.println("total vect dist is :" + vect_dist);
                            if ( vect_dist > 5.0)
                                res = false;
                        }
                    }

                    if ( res == true) // great this flip work
                    {
                        System.out.println("flip " + tryComp + " work");
                        JuncAssignWork = true;
                        break;
                    }
                    else //set back
                        comp[tryComp].mAxisInfo.transRotHis_finalTangent.set(oriVec);
                  } //for loop of k
                  if (JuncAssignWork == true)
                      break;
             } // for loop
        }

        if ( res == false)
        {
            System.out.println("try flip all final tangent one-by-one, no work!");
            System.out.println("check this shape out!!!");
            // July 23rd 2009
            //debug, may need to remove later
                //  this.nComponent = -1;

        }
        // step3. try a intensive all possible flip
        if ( res == false)
        {


              System.out.println("Intensive flip trial...");
              if ( tryFlip == false)
                    return;
             // this.nComponent = -1;
              int tryTimes= 1;

              for (tryTimes = 1; tryTimes <= Math.pow(2, nComponent) -1; tryTimes++)
             {
                    //key line  ---> flip the tangent dir
                    System.out.println("try to flip times " + tryTimes);
                    int[] flipState = new int[nComponent];
                    int divider = (int) Math.pow(2, nComponent-1);
                    int nowV = tryTimes;
                    for (j=0; j <nComponent; j++)
                    {
                        //System.out.println( j + " " + nowV + " " + divider);
                        flipState[j] = nowV / divider;
                        nowV = nowV % divider;
                        divider = divider /2;
                    }

                    //debug
                    for (j=0; j<nComponent; j++)
                        System.out.print( flipState[j] + " " );
                    System.out.println(" ");
                        System.out.println("nComp " + nComp);
                        System.out.println("nComponent " + nComponent);
                    for (j=1; j<=nComp; j++)
                        if (flipState[j-1] == 1)
                            comp[j].mAxisInfo.transRotHis_finalTangent.negate();

                    for (i=1; i<=nComp; i++)
                    {
                        comp[i].mAxisInfo.genArc( comp[i].mAxisInfo.rad, comp[i].mAxisInfo.arcLen);
                        comp[i].mAxisInfo.transRotMAxis(comp[i].mAxisInfo.transRotHis_alignedPt,
                        comp[i].mAxisInfo.transRotHis_finalPos,
                        comp[i].mAxisInfo.transRotHis_rotCenter,
                        comp[i].mAxisInfo.transRotHis_finalTangent,
                        comp[i].mAxisInfo.transRotHis_devAngle);
                        comp[i].RadApplied_Factory(); // since we didn't save these info
                    }

                    res = this.smoothizeMStick();
                    if ( res == false) // success to smooth
                    {
                        System.out.println("Fail to smooth while using info from a shapeSpec");
                        System.out.println("THIS SHOULD NOT HAPPEN4");
                    }

                    if ( res == true)
                    {
                        Point3d[] oriVecList = inSpec.getVectInfo();
                        double vect_dist = 0.0;
                        int nVect1 = this.obj1.nVect;
                        int nVect2 = inSpec.getNVect();
                        System.out.println("vec # check " + nVect1 + " " + nVect2);
                        if ( nVect1 != nVect2)
                        {
                            res = false;
                            System.out.println("vec # unmatch");
                        }
                        if ( res == true)
                        {
                            for (i= 1; i<= this.obj1.nVect; i++)
                            {
                                Point3d p1 = new Point3d(obj1.vect_info[i]);
                                Point3d p2 = oriVecList[i];
                                vect_dist += p1.distance(p2);
                            }
                            System.out.println("total vect dist is :" + vect_dist);
                            if ( vect_dist > 5.0)
                                res = false;
                        }
                    }

                    if ( res == true) // great this flip work
                    {
                        System.out.println("flip " + tryTimes+ " work");
                        break;
                    }
                    //flip back
                    for (j=1; j<=nComp; j++)
                        if (flipState[j-1] == 1)
                            comp[j].mAxisInfo.transRotHis_finalTangent.negate();

             } // for loop
        }

        // not implement yet
        //step4. change multiple tangent to the Junc/End Pt info
        if ( res == false)
        {
            System.out.println("try flip all intensive flip, still no work!");
            System.out.println("check this shape out!!!");
            System.out.println("check this shape out!!!");

                    //this.nComponent = -1;
        }

        this.parentStick = new MatchStick();

    }
    /**
     *    Function that we use to read a file with XML spec,
     *    and save those info into this class, and show it out
     *    Good for debug, and later analysis
     */
    public void genMatchStickFromFileData()
    {
        System.out.println("\nRead spec info from XML input file");
        String fname = "./sample/specXML_input.txt";
        //String fname = "./sample/specXML_input.txt";
        // read the file into a string and then tranform to spec
//        String in_specStr;
        StringBuffer fileData = new StringBuffer(1000);
        try
        {
            BufferedReader reader = new BufferedReader(
                new FileReader(fname));
            char[] buf = new char[1024];
            int numRead=0;
            while((numRead=reader.read(buf)) != -1){
                String readData = String.valueOf(buf, 0, numRead);
                //System.out.println(readData);
                fileData.append(readData);
                buf = new char[1024];

            }
            reader.close();
        }
        catch (Exception e)
        {
            System.out.println("error in read XML spec file");
            System.out.println(e);
        }

//        in_specStr = fileData.toString();

        //if the input file is MStickSpec
            //  MStickSpec inSpec = new MStickSpec();
            //inSpec = MStickSpec.fromXml(in_specStr);

        //if the input file is ShapeSpec
//        ShapeSpec s_spec = new ShapeSpec();
//        s_spec = ShapeSpec.fromXml(in_specStr);
        MStickSpec inSpec = new MStickSpec();
//        inSpec = s_spec.mStickSpec;

        //this is to make a spec which is old fashion without finalRotation info
        if ( inSpec.mAxis.finalRotation == null)
        {
            System.out.println("No final rotation info available...");
            inSpec.mAxis.finalRotation = new double[3];
            for (int i = 0; i<3; i++)
                inSpec.mAxis.finalRotation[i] = 0.0;
        }
        System.out.println("final rot info");
        for (int i=0; i<3; i++)
            System.out.println(" rot " + inSpec.mAxis.finalRotation[i]);
        this.genMatchStickFromShapeSpec(inSpec);

        System.out.println(comp[1].mAxisInfo.mPts[51]);
        System.out.println(comp[2].mAxisInfo.mPts[1]);
        //do the finalRotateHere, or already did in fromShapeSpec
        //this.finalRotateAllPoints( finalRotation[0], finalRotation[1], finalRotation[2]);
        boolean res = this.smoothizeMStick();
        if ( res == false) // success to smooth
        {
            System.out.println("Fail to smooth while using info from a file (in file)");
            System.out.println("THIS SHOULD NOT HAPPEN5");
        }


        //just for debug

        int nVect = inSpec.getNVect();
        int nFac = inSpec.getNFac();
        Point3d[] ivect_info = inSpec.getVectInfo();
        Vector3d[] inormMat_info = inSpec.getNormMatInfo();
        int[][] iFac_info = inSpec.getFacInfo();

        this.obj1.setInfo(nVect, ivect_info, inormMat_info, nFac, iFac_info);


        this.modifyMAxisFinalInfo();

        System.out.println(comp[4].mAxisInfo.mTangent[1]);
        System.out.println(comp[4].mAxisInfo.mTangent[51]);
        System.out.println("final tan" + comp[4].mAxisInfo.transRotHis_finalTangent);
   }

    public void genMatchStickRand()
    {
        int nComp;
        //double nCompDist = { 0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
        //double[] nCompDist = { 0, 0.1, 0.2, 0.4, 0.6, 0.8, 0.9, 1.00};
        //double[] nCompDist = {0, 0.05, 0.15, 0.35, 0.65, 0.85, 0.95, 1.00};
        double[] nCompDist = this.PARAM_nCompDist;
        nComp = stickMath_lib.pickFromProbDist(nCompDist);

        this.cleanData();
        //  debug
        //  nComp = 4;

        //The way we write like this can guarantee that we try to
        // generate a shape with "specific" # of components

       while (true)
       {
          while (true)
          {
            if (genMatchStick_comp(nComp) == true)
                break;
//            else
//                System.out.println("        Attempt to gen shape fail. try again");
          }

          this.finalRotation = new double[3];
          for (int i=0; i<3; i++)
              finalRotation[i] = stickMath_lib.randDouble(0, 360.0);

          //debug

          //finalRotation[0] = 90.0;
          //finalRotation[1] = 0.0;
          //finalRotation[2] = 0;

          //this.finalRotateAllPoints(finalRotation[0], finalRotation[1], finalRotation[2]);

          boolean res = this.smoothizeMStick();
          if ( res == true) // success to smooth
              break; //else we need to gen another shape
//          else
//              System.out.println("      Fail to smooth combine the shape. try again.");




       }

//       System.out.println("  End random MAxis Shape gen.\n");
       this.parentStick = new MatchStick();

     }

//    public void drawSkeleton()
//    {
//        int i;
//          if (showMode == 0)
//          {
//
//            for (i=1; i<=nComponent; i++)
//                {
//                //              comp[i].mAxisInfo.drawArc();
//                    float[][] colorCode= {  {1.0f, 1.0f, 1.0f},
//                                {1.0f, 0.0f, 0.0f},
//                                {0.0f, 1.0f, 0.0f},
//                                {0.0f, 0.0f, 1.0f},
//                                {0.0f, 1.0f, 1.0f},
//                                {1.0f, 0.0f, 1.0f},
//                                {1.0f, 1.0f, 0.0f},
//                                {0.4f, 0.1f, 0.6f} };
//
//
//                    comp[i].drawSurfPt( colorCode[i-1]);
//                   //debug
//
//                }
//          }
//          if (showMode == 1)
//            obj1.drawVect();
//
//        }

    public void drawSkeleton(TextureType tt, RGBColor color,String folderName,String descId) {
	    	if (doCenterShape &&  !alreadyCentered) {
	    		Point3d pt = new Point3d();
	    		pt.x = -xyPosition.x;
	    		pt.y = -xyPosition.y;
	    		pt.z = 0;
	    		obj1.translateBack(pt);

	    		this.obj1.scaleTheObj(8/externalSizeParam);
	    		alreadyCentered = true;
	    	}
	    	obj1.setTexSpec(texSpec);
	    	obj1.setTexFaceSpec(texFaceSpec);
	    	obj1.setViewport(viewport);
	    	obj1.setFrameNum(frameNum);

		obj1.drawVect(tt,color,folderName,descId);

		boundingBox = obj1.getBoundingBox();
		if (doClouds) {
			redraw_clouds();
		} else if (doLowPass) {
			redraw_lowPass();
		}
    }

    public void preloadImages(TextureType tt, String folderName,String descId) {
    		obj1.loadPhoto(folderName, descId, tt);
    }

     /**
    genMatchStick with nComp components
    */
    public boolean genMatchStick_comp(int nComp)
    {
        boolean showDebug = false;
//        System.out.println("  Start random MAxis Shape gen...");
        if ( showDebug)
            System.out.println("Generate new random mStick, with " + nComp + " components");
        int i;
        this.nComponent= nComp;
        //comp = new TubeComp[nComp+1];

        for (i=1; i<=nComp; i++)
            comp[i] = new TubeComp();
        // 1. create first component at the center of the space.
        this.createFirstComp();
        // 2. sequentially adding new components

        int nowComp = 2;
        double randNdx;
        boolean addSuccess;
            while (true)
        {
            if ( showDebug)
                System.out.println("adding new MAxis on, now # " +  nowComp);
            randNdx = stickMath_lib.rand01();
            if (randNdx < PROB_addToEndorJunc)
            {
                if (nJuncPt == 0 || stickMath_lib.rand01() < PROB_addToEnd_notJunc)
                    addSuccess = this.Add_MStick(nowComp, 1);
                else
                    addSuccess = this.Add_MStick(nowComp, 2);
            }
            else
            {
                if (stickMath_lib.rand01() < PROB_addTiptoBranch)
                    addSuccess = this.Add_MStick(nowComp, 3);
                else
                    addSuccess = this.Add_MStick(nowComp, 4);
            }
            if (addSuccess == true) // otherwise, we'll runModeRun this while loop again, and re-generate this component
                nowComp ++;
            if (nowComp == nComp+1)
                break;
                }

        //up to here, the eligible skeleton should be ready
        // 3. Assign the radius value
        this.RadiusAssign( 0); // no component to preserve radius
        // 4. Apply the radius value onto each component
        for (i=1; i<=nComponent; i++)
        {
            if( this.comp[i].RadApplied_Factory() == false) // a fail application
            {
               return false;
            }
        }


        // 5. check if the final shape is not working ( collide after skin application)


        if ( this.finalTubeCollisionCheck() == true)
        {
            if ( showDebug)
                System.out.println("\n FAIL the final Tube collsion Check ....\n");
            return false;
        }


        // Dec 24th 2008
        // re-center the shape before do the validMStickSize check!
        this.centerShapeAtOrigin(-1);
        // this.normalizeMStickSize();

//   System.out.println("after centering");
        if ( this.validMStickSize() ==  false)
        {
            if ( showDebug)
                System.out.println("\n FAIL the MStick size check ....\n");
            return false;
        }
        return true;



       }



    /**
      function check if the MStick is inside a BOX or not <BR>
      ( to prevent a shape extend too much outside one dimension)
    */
    private boolean validMStickSize()
    {
    	double maxRad = externalSizeParam; //deg
    	double screenDist = 500;

    	double radSize = screenDist * Math.tan(maxRad*Math.PI/180) / 2;

        int i, j;

        Point3d ori = new Point3d(0.0,0.0,0.0);
        double dis;
        for (i=1; i<=nComponent; i++)
            for (j=1; j<= comp[i].nVect; j++)
	        {
	            dis = comp[i].vect_info[j].distance(ori);
	            if ( dis > radSize )
	            {
	                  return false;
	            }
	        }
        return true;
    }

    /**
    * function check that if the final generated tube have remote collsion or not
    */
    private boolean finalTubeCollisionCheck()
    {
        int nComp = this.nComponent;
        boolean[][] connect = new boolean[nComp*2+1][nComp*2+1];
        boolean showDebug = false;
        // 1. build up the connection map
        int i, j, k, m;
        int a,b, cpt1, cpt2, part_a, part_b;
        //System.out.println("final Tube collision check");

        for (i = 1 ; i<=  this.nJuncPt; i++)
          for (j=1; j<= JuncPt[i].nComp; j++)
            for (k=j+1; k<= JuncPt[i].nComp; k++)
                {
                a =    JuncPt[i].comp[j];
            b =    JuncPt[i].comp[k];
            cpt1 = JuncPt[i].uNdx[j];
            cpt2 = JuncPt[i].uNdx[k];
            if (cpt1 == 1)
            {
               if (cpt2 == 1)
                connect[a*2-1][b*2-1] = true;
                           else if ( cpt2 == 51)
                connect[a*2-1][b*2] = true;
               else
               {
                connect[a*2-1][b*2-1] = true;
                connect[a*2-1][b*2] = true;
               }
            }
                        else if (cpt1 == 51)
            {
               if (cpt2 == 1)
                connect[a*2][ b*2-1] = true;
                           else if (cpt2 == 51)
                connect[a*2][b*2] = true;
               else
               {
                connect[a*2][b*2-1] = true;
                connect[a*2][b*2] = true;
               }
            }
            else
            {
               if (cpt2 == 1)
               {
                connect[a*2-1][b*2-1] = true;
                connect[a*2][b*2-1] = true;
               }
                           else if (cpt2 == 51)
               {
                connect[a*2-1][b*2] = true;
                connect[a*2][b*2] = true;
               }
               else
                System.out.println("Connection Map Generating:  this should not be possible...error checking plz");

                        }

             }
        // make connect to be symmetric
        for (i = 1 ; i<= nComp*2; i+=2)
                connect[i][i+1] = true;

        for (i = 1 ; i <= nComp*2 ; i++)
            for (j = 1 ; j<= nComp *2 ; j++)
                   if (connect[i][j])
                   connect[j][i] = true;

        // May 19th , do a branch one more step connection!
        // so, the branch protrusion and end protrusion will be regard as connected in the root part
        int st_ndx = 0;
        for (i = 1 ; i<=  this.nJuncPt; i++)
          for (j=1; j<= JuncPt[i].nComp; j++)
           for (k=j+1; k<= JuncPt[i].nComp; k++)
        {
            a =    JuncPt[i].comp[j];
            b =    JuncPt[i].comp[k];
            cpt1 = JuncPt[i].uNdx[j];
            cpt2 = JuncPt[i].uNdx[k];
            if ( cpt1 != 1 && cpt1 != 51)
            {
                if ( cpt2 == 1 )
                st_ndx = b*2-1;
                else if (cpt2 == 51)
                st_ndx = b*2;

                for (m = 1 ; m <= nComp * 2; m++)
                {
                if ( connect[a*2][m] )
                {
                    connect[st_ndx][m] = true;
                    connect[m][st_ndx] = true;
                }

                if ( connect[a*2-1][m] )
                {
                    connect[st_ndx][m] = true;
                    connect[m][st_ndx] = true;
                }
                 }
            }

            if (cpt2 != 1 && cpt2 != 51)
            {
                if (cpt1 == 1 )
                st_ndx = a*2-1;
                else if (cpt1 == 51)
                st_ndx = a*2;

                for (m = 1 ; m <= nComp * 2; m++)
                {
                if ( connect[b*2][m] )
                {
                    connect[st_ndx][m] = true;
                    connect[m][ st_ndx] = true;
                }

                if ( connect[b*2-1][m])
                {
                    connect[st_ndx][ m] = true;
                    connect[m][st_ndx] = true;
                }
                }

            }

        } // triple for loop for branch addition


        // 2. check the closeness relation
        boolean check_res = false;

            for ( i = 1 ; i <= nComp*2 ; i++)
           for (j=i+1; j<=nComp*2; j++)
                     if (connect[i][j] == false)
             {
                a = (int) Math.ceil((double)i/2.0);
                    b = (int) Math.ceil((double)j/2.0);
                    part_a = (i+1)%2; // make part 0 be the earlier part
            part_b = (j+1)%2; // and the part1 be the later part

            check_res = finalTubeCollisionCheck_SUB_checkCloseness( a, part_a, b, part_b);
            if ( check_res)
            {
                if (showDebug)
                {
                    System.out.println("collision detected btw component " + a + " & " + b);
                    System.out.println("the part are respectively " + part_a +" & " + part_b);
                }
                return check_res;
            }
              }


        return check_res; // return true if there is closeness found


    }
    /**
        Sub function of finalTubeCollsionCheck
        This function calculate if part of two tubes are too near to each other or not
    */
    private boolean finalTubeCollisionCheck_SUB_checkCloseness( int compA, int part1, int compB, int part2)
    {
        boolean showDebug = false;
        double tolerance, nowdist;
        int nSamplePts = 51;
        int midPt = (nSamplePts+1)/2;
        int iStart, iEnd, jStart, jEnd, i, j;
        Point3d p1, p2;

        if (part1 == 0) // first half
        {  iStart = 1;          iEnd = midPt -7; }
        else
        {  iStart = midPt +7;      iEnd = nSamplePts;}

        if (part2 == 0)
        {  jStart = 1;          jEnd = midPt - 7; }
        else
        {  jStart = midPt +7;   jEnd = nSamplePts;}


        for (i = iStart ; i<=iEnd; i++)
          for (j=jStart; j<=jEnd; j++)
          {
            p1 = comp[compA].mAxisInfo.mPts[i]; // since we didn't chg p1, p2 's value, it is ok to use = here
            p2 = comp[compB].mAxisInfo.mPts[j];

            nowdist = p1.distance(p2);
            tolerance = (comp[compA].radiusAcross[i] + comp[compB].radiusAcross[j]);


            if ( nowdist <= tolerance) // too near by here
            {
                if (showDebug)
                {
                    System.out.println("i " + i + "  j " + j);
                    System.out.println("now dist " + nowdist + " tolerance " + tolerance);
                    System.out.println("tube " + compA + "tube " + compB + " collide");
                }
                            return true;
                        }
          }

        return false;
    }

        /**
        Assign the radius value to the Match Stick.
        The radius value will be randomly chosen in reasonable range
        */
    private void RadiusAssign(int nPreserve)
    {
        double rMin, rMax;
        double nowRad, u_value, tempX;
        int i, j;
            // 0. initialize to negative value
        for (i= nPreserve+1; i<=nComponent; i++)
        {
        comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
        }
            // 1. assign at JuncPt
        for (i=1; i<=nJuncPt; i++)
        {
          if ( JuncPt[i].rad == 100.0) // a whole new JuncPt
          {
             rMin = -10.0; rMax = 100000.0;
                 int nRelated_comp = JuncPt[i].nComp;
                 for (j = 1 ; j <= nRelated_comp; j++)
             {
                    rMin = Math.max( rMin, comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 10.0);
                    tempX = Math.min( 0.5 *comp[JuncPt[i].comp[j]].mAxisInfo.rad,
                 comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 3.0);
                    rMax = Math.min( rMax, tempX);
             }

                 if (rMax < rMin)
                        System.out.println(" In radius assign, ERROR: rMax < rMin");

                     // select a value btw rMin and rMax
                 nowRad = stickMath_lib.randDouble( rMin, rMax);
                     // assign the value to each component
             JuncPt[i].rad = nowRad;

                     for (j = 1 ; j <= nRelated_comp ; j++)
             {
                      u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                      if ( Math.abs( u_value - 0.0) < 0.0001)
              {
                        comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
              }
                      else if ( Math.abs(u_value - 1.0) < 0.0001)
              {
                comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
              }
                      else // middle u value
              {
                comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
              }

                  }
           }
           else // JuncPt.rad != 100.0, means this JuncPt is an existing one
                    {
            for (j=1; j<= JuncPt[i].nComp; j++)
              if ( JuncPt[i].comp[j] > nPreserve) // the component which need to assign radius
            {
                nowRad = JuncPt[i].rad;
                u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                        if ( Math.abs( u_value - 0.0) < 0.0001)
                {
                            comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                    comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
                }
                        else if ( Math.abs(u_value - 1.0) < 0.0001)
                {
                    comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                    comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
                }
                        else // middle u value
                {
                    comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                    comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
                }
            }

            }
        } // loop nJuncPt

        // 2. assign at endPt
        for ( i = 1 ;  i <= nEndPt ; i++)
          if ( endPt[i].comp > nPreserve ) // only do the radius assign for endPt with component we need
        {

                int nowComp = endPt[i].comp;
                u_value = ((double)endPt[i].uNdx -1.0 ) / (51.0 -1.0);

            //rMin = mStick.comp(nowComp).arcLen / 10.0;
            rMin = 0.00001; // as small as you like
            rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);

            // select a value btw rMin and rMax
            nowRad = stickMath_lib.randDouble( rMin, rMax);

            endPt[i].rad = nowRad;

            if ( Math.abs( u_value - 0.0) < 0.0001)
            {
            comp[nowComp].radInfo[0][0] = 0.0;
            comp[nowComp].radInfo[0][1] = nowRad;
            }
            else if (Math.abs(u_value - 1.0) < 0.0001)
            {
            comp[nowComp].radInfo[2][0] = 1.0;
            comp[nowComp].radInfo[2][1] = nowRad;
                    }
            else // middle u value
                 System.out.println( "error in endPt radius assignment");

                }

        // 3. other middle Pt
          for ( i = nPreserve+1 ; i <= nComponent ; i++)
              if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
            {
                int branchPt = comp[i].mAxisInfo.branchPt;
                u_value = ((double)branchPt-1.0) / (51.0 -1.0);

                rMin = comp[i].mAxisInfo.arcLen / 10.0;
                rMax = Math.min(comp[i].mAxisInfo.arcLen / 3.0, 0.5 * comp[i].mAxisInfo.rad);
                nowRad = stickMath_lib.randDouble( rMin, rMax);
                comp[i].radInfo[1][0] = u_value;
                comp[i].radInfo[1][1] = nowRad;
                }
    }

        /**
         check if the first several mAxisArc are too nearby to each other
         @param firstNComp specify till what component, we want to check
        */
    private boolean checkSkeletonNearby(int firstNComp)
        {
        boolean showDebug = false;
        int nComp = firstNComp;
        boolean[][] connect = new boolean[25][25]; //make it large enough for 8 component, not a large waste of space

        // 1. build up the connection map
        int i, j, k;
        int a,b, cpt1, cpt2, part_a, part_b;
        if (showDebug)
        {
            System.out.println("check skeleton nearby, nJuncPt : " + nJuncPt);
            for (i=1; i<=nJuncPt; i++)
                JuncPt[i].showInfo();
        }

        for (i = 1 ; i<=  this.nJuncPt; i++)
          for (j=1; j<= JuncPt[i].nComp; j++)
            for (k=j+1; k<= JuncPt[i].nComp; k++)
                {
                a =    JuncPt[i].comp[j];
            b =    JuncPt[i].comp[k];
            cpt1 = JuncPt[i].uNdx[j];
            cpt2 = JuncPt[i].uNdx[k];
            if (cpt1 == 1)
            {
               if (cpt2 == 1)
                connect[a*2-1][b*2-1] = true;
                           else if ( cpt2 == 51)
                connect[a*2-1][b*2] = true;
               else
               {
                connect[a*2-1][b*2-1] = true;
                connect[a*2-1][b*2] = true;
               }
            }
                        else if (cpt1 == 51)
            {
               if (cpt2 == 1)
                connect[a*2][ b*2-1] = true;
                           else if (cpt2 == 51)
                connect[a*2][b*2] = true;
               else
               {
                connect[a*2][b*2-1] = true;
                connect[a*2][b*2] = true;
               }
            }
            else
            {
               if (cpt2 == 1)
               {
                connect[a*2-1][b*2-1] = true;
                connect[a*2][b*2-1] = true;
               }
                           else if (cpt2 == 51)
               {
                connect[a*2-1][b*2] = true;
                connect[a*2][b*2] = true;
               }
               else
                System.out.println("Connection Map Generating:  this should not be possible...error checking plz");

                        }

             }
        // make connect to be symmetric
        for (i = 1 ; i<= nComp*2; i+=2)
                connect[i][i+1] = true;

        for (i = 1 ; i <= nComp*2 ; i++)
            for (j = 1 ; j<= nComp *2 ; j++)
                   if (connect[i][j])
                   connect[j][i] = true;

            //debug
        if (showDebug)
        {
            System.out.println("connection map");
               for (i=1; i<=nComp*2; i++)
           {
            for (j=1; j<=nComp*2; j++)
            if (connect[i][j])
                System.out.print("1 ");
            else
                System.out.print("0 ");
            System.out.println(" ");
           }
            }
        // 2. check the closeness relation
        boolean check_res = false;

            for ( i = 1 ; i <= nComp*2 ; i++)
           for (j=i+1; j<=nComp*2; j++)
                     if (connect[i][j] == false)
             {
                a = (int) Math.ceil((double)i/2.0);
                    b = (int) Math.ceil((double)j/2.0);
                    part_a = (i+1)%2; // make part 0 be the earlier part
            part_b = (j+1)%2; // and the part1 be the later part

            check_res = checkSkeletonNearby_checkCloseness( a, part_a, b, part_b);
            if ( check_res)
            {
                if (showDebug)
                {
                    System.out.println("collsion detected btw component " + a + " & " + b);
                    System.out.println("the part are respectively " + part_a +" & " + part_b);
                }
                return check_res;
            }
              }


        return check_res; // return true if there is closeness found
        }
        /**
        Check if two component skeleton are too nearby or not
        A function that be used in checkSkeletonNearby ONLY!
        */
    private boolean checkSkeletonNearby_checkCloseness(int compA, int part1, int compB, int part2)
    {
        boolean showDebug = false;
        final double NearByFactor = 7.0;
        double tolerance, nowdist;
            tolerance =  (comp[compA].mAxisInfo.arcLen /NearByFactor + comp[compB].mAxisInfo.arcLen/NearByFactor);
        if (showDebug)
        {
          System.out.println(" Comp " + compA + " part " + part1 + " vs. Comp " + compB + " part " + part2);
          System.out.println(" the tolerance is " + tolerance + " with arcLen1 " + comp[compA].mAxisInfo.arcLen +
                    " and arcLen 2 " + comp[compB].mAxisInfo.arcLen);
        }
        int nSamplePts = 51;
        int midPt = (nSamplePts+1)/2;
        int iStart, iEnd, jStart, jEnd, i, j;

        Point3d p1, p2;
        if (part1 == 0) // first half
        {  iStart = 1;          iEnd = midPt; }
        else
        {  iStart = midPt;      iEnd = nSamplePts;}

        if (part2 == 0)
        {  jStart = 1;          jEnd = midPt; }
        else
        {  jStart = midPt;  jEnd = nSamplePts;}


        for (i = iStart ; i<=iEnd; i++)
          for (j=jStart; j<=jEnd; j++)
          {
            p1 = comp[compA].mAxisInfo.mPts[i]; // since we didn't chg p1, p2 's value, it is ok to use = here
            p2 = comp[compB].mAxisInfo.mPts[j];

            nowdist = p1.distance(p2);
            if ( nowdist <= tolerance) // too nearby here
            {
                if (showDebug)
                {
                    System.out.println("check skeleton nearby, find closeness" + i + " " +j);
                    System.out.println("p1 "+ p1);
                    System.out.println("p2 "+ p2);
                    System.out.println("dist: "+ nowdist);
                    if ( tempStick != null)
                    {
                        System.out.println("old p1 " + tempStick.comp[compA].mAxisInfo.mPts[i]);
                        System.out.println("old p2 " + tempStick.comp[compB].mAxisInfo.mPts[j]);
                    }

                }
                            return true;
                        }
          }
        // if can achieve here, there is no collsion
        return false;
    }

    /**
        Adding a new MAxisArc to a MatchStick
        @param nowComp the index of the new added mAxis
        @param type type from 1~4, indicate the type of addition, eg. E2E, E2J, E2B, B2E
        */
    private boolean Add_MStick(int nowComp, int type)
    {
        // Add new component to a existing partial MStick
        // 4 types of addition are possible , specified by type
        // 1. type == 1: E2E connection
        // 2. type == 2: E2J connection
        // 3. type == 3: E2B connection
        // 4. type == 4: B2E conneciton

                //shared variable Delcaration
        boolean showDebug = false;
        //final double TangentSaveZone = Math.PI / 4.0;
        int i;
        int trialCount = 1; // an indicator that if something try too many time, then just give up
        if (showDebug)
        {
            System.out.println("In AddMStick: nowComp " + nowComp + " type: " + type);
            System.out.println("now nEndPt " + nEndPt + " , and nJuncPt " + nJuncPt);
        }
        // random get a new MAxisArc
        MAxisArc nowArc = new MAxisArc();
        nowArc.genArcRand();



        //debug
        // if (nowComp != 2)
        //  type = 2;
        // else
        //  type = 4;
        if (type == 1) // Adding the new Comp end-to-end
        {
           // 1. pick an endPt

            int nowPtNdx;
            trialCount = 1;
            while (true)
            {
                    nowPtNdx = stickMath_lib.randInt(1, this.nEndPt);
                if (endPt[nowPtNdx].rad > 0.2)
                    break; // we find a good endPt
                trialCount++;
                if (trialCount == 100)
                    return false; // can't find an eligible endPt
            }
           // 2. trnasRot the nowArc to the correction configuration
            int alignedPt = 1;
            Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
            Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
            Vector3d finalTangent = new Vector3d();
            trialCount = 1;
            while (true)
            {
                finalTangent = stickMath_lib.randomUnitVec();
                if ( oriTangent.angle(finalTangent) > TangentSaveZone ) // angle btw the two tangent vector
                    break;
                if ( trialCount++ == 300)
                    return false;
            }
            double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


            // 3. update the EndPT to JuncPt
            nJuncPt++;
            int[] compList = { endPt[nowPtNdx].comp, nowComp};
            int[] uNdxList = { endPt[nowPtNdx].uNdx, 1};
            Vector3d[] tangentList = { oriTangent, finalTangent};
            this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 2, tangentList, compList, endPt[nowPtNdx].rad);
            comp[nowComp].initSet( nowArc, false, 1); // the MAxisInfo, and the branchUsed

                // 2.5 call the function to check if this new arc is valid
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nJuncPt] = null;
                nJuncPt--;
                return false;
                        }
            // 4. generate new endPt
            this.endPt[nowPtNdx].setValue(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
            // 5. save this new Comp

        }
        else if (type == 2) // end to Junction connection
        {
            //1. pick a Junction Pt

            if (this.nJuncPt == 0)
            {
                System.out.println("ERROR, should not choose type 2 addition when nJuncPt = 0");
                return false;
            }
            int nowPtNdx = stickMath_lib.randInt(1, this.nJuncPt);
            //2. transRot the newComp
            int alignedPt = 1;
            Point3d finalPos = new Point3d(JuncPt[nowPtNdx].pos);
            Vector3d finalTangent = new Vector3d();
            trialCount = 1;
            while (true)
            {
                finalTangent = stickMath_lib.randomUnitVec();
                boolean flag = true;
                for (i=1; i<= JuncPt[nowPtNdx].nTangent; i++)
                {
                    if ( finalTangent.angle( JuncPt[nowPtNdx].tangent[i]) <= TangentSaveZone)
                        flag = false;
                }
                if (flag == true) // i.e. all the tangent at this junction is ok for this new tangent
                    break;
                if ( trialCount++ == 300)
                    return false;
            }
            double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);


            //3. update the JuncPt & endPt info and add the new Comp
            JuncPt_struct old_JuncInfo = new JuncPt_struct();
            old_JuncInfo.copyFrom(JuncPt[nowPtNdx]);
            this.JuncPt[nowPtNdx].addComp(nowComp, 1, nowArc.mTangent[1]);
            comp[nowComp].initSet(nowArc, false, 2);
                // 2.5 call the function to check if this new arc is valid
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nowPtNdx].copyFrom(old_JuncInfo);
                return false;
                        }
            nEndPt++;
            this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);

        }
        else if (type == 3) //end-to-branch connection
        {
             // 1. select a existing comp, with free branch
            int pickedComp;
            while(true)
            {
                pickedComp = stickMath_lib.randInt(1, nowComp-1); // one of the existing component
                if ( comp[pickedComp].branchUsed == false)
                    break;
                if (showDebug)
                    System.out.println("pick tube with branch unused");
            }
             // 2. transrot the newComp
            int alignedPt = 1;
            int nowUNdx = comp[pickedComp].mAxisInfo.branchPt;
            Point3d finalPos = new Point3d( comp[pickedComp].mAxisInfo.mPts[nowUNdx]);
            Vector3d oriTangent1 = new Vector3d( comp[pickedComp].mAxisInfo.mTangent[nowUNdx]);
            Vector3d oriTangent2 = new Vector3d();
            Vector3d finalTangent = new Vector3d();
            oriTangent2.negate(oriTangent1);
            //System.out.println(oriTangent1);
            //System.out.println(oriTangent2);
            trialCount = 1;
            while(true)
            {
                finalTangent = stickMath_lib.randomUnitVec();
                if ( finalTangent.angle(oriTangent1) > TangentSaveZone &&
                     finalTangent.angle(oriTangent2) > TangentSaveZone    )
                    break;
                if ( trialCount++ == 300)
                    return false;
            }
            double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
             // 2.5 check if newComp valid
             // 3. update the JuncPt & endPt info
            nJuncPt++;
            int[] compList = { pickedComp, nowComp};
            int[] uNdxList = { nowUNdx, 1};
            Vector3d[] tangentList = { oriTangent1, oriTangent2, finalTangent};
            int[] ownerList = { pickedComp, pickedComp, nowComp};
            double rad = 100.0;
            rad = comp[pickedComp].radInfo[1][1]; // if it is existing tube, then there will be a value
                //otherwise, it should be initial value of 100.0
            this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);
            //JuncPt[nJuncPt].showInfo();
                // 2.5 call the function to check if this new arc is valid
            comp[nowComp].initSet(nowArc, false, 3);
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nJuncPt] = null;
                nJuncPt--;
                return false;
                        }
            nEndPt++;
            this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);
            comp[pickedComp].branchUsed = true;


        }
        else if (type == 4) // add branch to the existing EndPt
        {
            // 1. pick an EndPt
            trialCount = 1;
            int nowPtNdx;
            trialCount = 1;
            while (true)
            {
                    nowPtNdx = stickMath_lib.randInt(1, this.nEndPt);
                if (endPt[nowPtNdx].rad > 0.2)
                    break; // we find a good endPt
                trialCount++;
                if (trialCount == 100)
                    return false; // can't find an eligible endPt
            }
            // 2. transRot newComp
            int nowUNdx = nowArc.branchPt;
            int alignedPt = nowUNdx;
            Vector3d rev_tangent = new Vector3d();
            Point3d finalPos = new Point3d(endPt[nowPtNdx].pos);
            Vector3d oriTangent = new Vector3d(endPt[nowPtNdx].tangent);
            Vector3d finalTangent = new Vector3d();
            trialCount = 1;
            while(true)
            {
                finalTangent = stickMath_lib.randomUnitVec();

                rev_tangent.negate(finalTangent);
                if ( oriTangent.angle(finalTangent) > TangentSaveZone &&
                     oriTangent.angle(rev_tangent) > TangentSaveZone    )
                    break;
                if ( trialCount++ == 300)
                    return false;
            }
            double devAngle = stickMath_lib.randDouble(0.0, 2 * Math.PI);
            nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);
            // 2.5 check Nearby Situtation
            // 3. update JuncPt & endPt info
            nJuncPt++;
            int[] compList = { endPt[nowPtNdx].comp, nowComp};
            int[] uNdxList = { endPt[nowPtNdx].uNdx, nowUNdx};
            Vector3d[] tangentList = { oriTangent, finalTangent, rev_tangent};
            int[] ownerList = {endPt[nowPtNdx].comp, nowComp, nowComp};
            double rad;
            rad = endPt[nowPtNdx].rad;
            this.JuncPt[nJuncPt] = new JuncPt_struct(2, compList, uNdxList, finalPos, 3, tangentList, ownerList, rad);

            // 2.5 call the function to check if this new arc is valid
            comp[nowComp].initSet(nowArc, true, 4);
            if (this.checkSkeletonNearby(nowComp) == true)
            {
                JuncPt[nJuncPt] = null;
                nJuncPt--;
                return false;
                        }
            // 4. generate 2 new endPt
            this.endPt[nowPtNdx].setValue(nowComp, 1, nowArc.mPts[1], nowArc.mTangent[1], 100.0);
            nEndPt++;
            this.endPt[nEndPt] = new EndPt_struct(nowComp, 51, nowArc.mPts[51], nowArc.mTangent[51], 100.0);

        }

        if ( showDebug)
            System.out.println("end of add tube func successfully");
        return true;
        // call the check function to see if the newly added component violate the skeleton nearby safety zone.
    }

        /**
         Deal with the creation of first MAxisArc component
        */
    private void createFirstComp() // create the first component of the MStick
    {
        Point3d finalPos = new Point3d(0,0,0); //always put at origin;
        Vector3d finalTangent = new Vector3d(0,0,0);
        finalTangent = stickMath_lib.randomUnitVec();
       // System.out.println("random final tangent is : " + finalTangent);
        double devAngle = stickMath_lib.randDouble(0.0, Math.PI * 2);
        int alignedPt = 26; // make it always the center of the mAxis curve
        MAxisArc nowArc = new MAxisArc();
        nowArc.genArcRand();
        nowArc.transRotMAxis(alignedPt, finalPos, alignedPt, finalTangent, devAngle);

        comp[1].initSet( nowArc, false, 0); // the MAxisInfo, and the branchUsed
        //update the endPt and JuncPt information
        this.endPt[1] = new EndPt_struct(1, 1, comp[1].mAxisInfo.mPts[1], comp[1].mAxisInfo.mTangent[1] , 100.0);
        this.endPt[2] = new EndPt_struct(1, 51, comp[1].mAxisInfo.mPts[51], comp[1].mAxisInfo.mTangent[51], 100.0);
        this.nEndPt = 2;
        this.nJuncPt = 0;

//      System.out.println(endPt[1]);
//      System.out.println(endPt[2]);
        }

    /**
        Set the shape one step back to its parent
    */
    public void setBackToParent()
    {
        this.copyFrom(this.parentStick);
    }
    /**
        A public function that will start generating an offspring of this existing shape
        The parent is the current shape.
        The result will be stored in this object
    */
    public boolean mutate(int debugParam)
    {

        final int MaxMutateTryTimes = 10;
        final int MaxAddTubeTryTimes = 15;
        final int MaxCompNum = 8;
        final int MinCompNum = 2;
        final int MaxDeletionNum = 1;
        boolean showDebug = false;

        if ( showDebug)
        {
            System.out.println("  Now start MAxis Mutation: ");
        }
        MatchStick oldCopy_stick = new MatchStick();
        oldCopy_stick.copyFrom( this);
        this.parentStick = new MatchStick();
        this.parentStick.copyFrom(this); // set the parentStick
        // 4 possible task for each tube
        // [ 1.nothing 2.replace whole 3. fine chg 4. Remove it]
        // The distribution will be different for center & leaf stick
//        double[] probDist;
        double[] prob_leaf = {0.4, 0.6, 0.8, 1.0};
        //double[] prob_center = {0.6, 0.8, 1.0, 1.0};
        double[] prob_center = {0.6, 0.6, 1.0, 1.0};
        double[] prob_addNewTube = { 1.0, 0.0, 1.0}; // 1/3 no add , 1/3 add 1, 1/3 add 2 tubes
//        if ( MaxAdditionNum == 1) // only allow one addition
//        {
            if ( this.nComponent <= 1)
            {
                prob_addNewTube[0] = 0.0;
                prob_addNewTube[1] = 1.0;
            }
            else if ( this.nComponent >= 2 && this.nComponent <=3)
            {
                prob_addNewTube[0] = 0.5;
                prob_addNewTube[1] = 1.0;
            }
            else if ( this.nComponent >= 4)
            {
                prob_addNewTube[0] = 1.0;
                prob_addNewTube[1] = 0.0;
            }
//        }
//        else if ( MaxAdditionNum > 2)
//             System.out.println("This should not be true");
        this.decideLeafBranch();

        int i;
        int old_nComp;
        int[] task4Tube = new int[nComponent+1];
        int[] task4Tube_backup = new int[nComponent+1];
        int nAddTube, nRemoveTube, nResultTube;
        boolean showDebugInfo = false;
        // 1. decide what kind of modification should go on
        int nChgTotal;
        int minChgTotal = 1;
        int maxChgTotal = 1;
        while (true)
        {
            boolean noChgFlg = true;
            for (i=1; i<=nComponent; i++)
            {
                if (  LeafBranch[i] == true)
                    task4Tube[i] = stickMath_lib.pickFromProbDist( prob_leaf);
                else
                    task4Tube[i] = stickMath_lib.pickFromProbDist( prob_center);

                if (task4Tube[i] != 1) noChgFlg = false; // at least one chg will occur

            }
            nAddTube = stickMath_lib.pickFromProbDist( prob_addNewTube) - 1;
            nRemoveTube = 0;
            for (i=1; i<=nComponent; i++)
                if (task4Tube[i] == 4)
                    nRemoveTube++;
            nResultTube = nComponent + nAddTube - nRemoveTube;

            // calculate nChgTotal
            nChgTotal = 0;
            for (i=1; i<=nComponent; i++)
                if (task4Tube[i] != 1)
                    nChgTotal++;
            nChgTotal += nAddTube;
            // so the # of nChgTotal means the # of tubes been ( modified or removed) + # of tube added
            if ( nChgTotal > maxChgTotal || nChgTotal < minChgTotal)
            {
                //if ( showDebug)
                //  System.out.println("nChgtotal is now " + nChgTotal);
                continue; // we don't want to small or too big change
            }
            if ( noChgFlg == false && nResultTube <= MaxCompNum  && nResultTube >= MinCompNum
                && nRemoveTube <= MaxDeletionNum ) // a legal condition
                break;

            if (showDebugInfo)
            {
                if (noChgFlg == true)
                    System.out.println("        No chg is found...so need re-try");

            }
        }

        //debug
        if (debugParam == 1)
        {

            //only remove 1 component each time
            for (i=1; i<=nComponent; i++)
            {
                task4Tube[i] = 1;
            }

            while (true)
            {
                i =stickMath_lib.randInt(1, nComponent);
                if (LeafBranch[i] == true)
                {
                    task4Tube[i] = 4;
                    break;
                }
            }

            nRemoveTube = 1;
            nAddTube = 0;
        }
        else if ( debugParam == 2)
        {
            nRemoveTube = 0;
            for (i=1; i<=nComponent; i++)
                task4Tube[i] = 1;


            nAddTube = 1;
        }
        else if ( debugParam == 3)
        {
            nRemoveTube = 0;
            nAddTube = 0;
            for (i=1; i<=nComponent; i++)
                task4Tube[i] = 1;
            int randComp  =stickMath_lib.randInt(1, nComponent);
            task4Tube[randComp] = 2;
        }
        else if ( debugParam == 4)
        {
            nRemoveTube = 0;
            nAddTube = 0;
            for (i=1; i<=nComponent; i++)
                task4Tube[i] = 1;
            int randComp  =stickMath_lib.randInt(1, nComponent);
            //debug
            //randComp = 1;
            task4Tube[randComp] = 3;

        }
//


        if (showDebugInfo) // show out what to do on each tube
        {
            System.out.println("        The task for the tubes are:");
            for (i=1; i<=nComponent; i++)
            {
                if (task4Tube[i] == 1)
                    System.out.println("            Tube " + i + " --> do nothing");
                else if ( task4Tube[i] == 2)
                    System.out.println("            Tube " + i + " --> replace whole tube");
                else if ( task4Tube[i] == 3)
                    System.out.println("            Tube " + i + " --> fine morph");
                else if ( task4Tube[i] == 4)
                    System.out.println("            Tube " + i + " --> remove it");
            }
            System.out.println("            Add " + nAddTube +" at the end \n");
        }


        // Now start the part of really doing the morphing

        // Dec 24th 2008.
        // At this point, we decide what kind of morphing to do
        // but, sometimes, some details will fail.
        // what I would like to do is try the morph several times before give up

        //March 10th 2009.
        //This is a bug I found after recording for a while
        //everytime we should load the task4Tube from the back
        //since if we re-do the mutate, the task4Tube might already
        //change during the previous manipulation.
        for (i=1; i<=nComponent; i++)
            task4Tube_backup[i] = task4Tube[i];

        int mutateTryTimes = 1;
        boolean successMutateTillNow;
        for (mutateTryTimes = 1; mutateTryTimes <= MaxMutateTryTimes; mutateTryTimes++)
        {
            //load the backup of task4Tube
            for (i=1; i<=nComponent; i++)
                task4Tube[i] = task4Tube_backup[i];

            if ( showDebug)
                System.out.println("In mutate, try times: " + mutateTryTimes);
            successMutateTillNow = true;
            //1. remove the stick
            boolean[] removeFlg = new boolean[nComponent+1];
            for (i=1; i<=nComponent; i++)
                if (task4Tube[i] == 4)
                    removeFlg[i] = true;
            old_nComp = nComponent; // since this number will chg later in removeComponent
            if (nRemoveTube > 0) // else , we can skip this procedure
                this.removeComponent( removeFlg);

            //2. fine tune and replacement
            //  2.1 remap the task4Tube
            {
                int counter =1 ;
                for (i=1; i<= old_nComp; i++)
                    if ( task4Tube[i] != 4)
                        task4Tube[counter++] = task4Tube[i];
            }
            //2.2 really doing the fine tune & replace
            for (i=1; i<= nComponent; i++)
            {
                boolean res = true;
                if (task4Tube[i] == 2) // replace
                    res = this.replaceComponent(i);
                if (task4Tube[i] == 3) // fine tune
                    res = this.fineTuneComponent(i);

                // if res == false, we want to go out to big Trial loop & try again
                if ( res == false)
                {
                    this.copyFrom( oldCopy_stick);
                    successMutateTillNow = false;
                    //return false;
                }
            }
            if ( successMutateTillNow == false) continue;

            //3. Add new tube on the shape
            // we will try to add several times locally
            if (nAddTube > 0)
            {
                MatchStick tempStoreStick = new MatchStick();
                tempStoreStick.copyFrom(this);
                int addtube_trytime = 0;
                while (true)
                {
                    boolean res = this.addTubeMutation(nAddTube);
                    if ( res == true)
                        break;
                    else // fail, restore
                    {
//                        System.out.println("\nIn mutation: add tube, restore info, trytime = " + addtube_trytime);
                        addtube_trytime++;
                        if ( addtube_trytime > MaxAddTubeTryTimes)
                        {
                            System.out.println("\nfail to add tube (try 15 times), give up\n");
                            this.copyFrom( oldCopy_stick);
                            //return false; // directly regard as a fail
                            successMutateTillNow = false;
                            break;
                        }
                    }
                    this.copyFrom(tempStoreStick);
                }
            }
            if ( successMutateTillNow == false) continue;

            // 5. reassign the radius value at junction Pt
            this.MutateSUB_reAssignJunctionRadius();

            // 6. translate the shape, so that the first comp is centered at origin.
//            this.centerShapeAtOrigin(-1);

            if ( this.validMStickSize() == false)
            {
                this.copyFrom( oldCopy_stick);
                //return false;
                successMutateTillNow = false;
            }
            if ( successMutateTillNow == false) continue;

//            this.changeFinalRotation();

            //Final. smoothize final result
            boolean res = this.smoothizeMStick();
            if ( res == true) // success to smooth
                return true;
            else
            {
//                System.out.println("In mutate shape, the final smooth fail!!!!!!!!\n.....");
                this.copyFrom( oldCopy_stick);
                successMutateTillNow = false;
            }

        }

        return false; // after try mutate loop 10 times
    }

    /**
     *   A function that randomly rotate the final object in a limit range
     */
    private boolean changeFinalRotation()
    {
        double degX, degY, degZ, sum_deg;
        // randomly +/- ? degree to newLogInfo rotation
        double volatileRate = this.ChangeRotationVolatileRate;
        // if ChangeRotationVolatileRate = 0.1, --> 90% chance no change

        //volatileRate = 10.0; // means always do final rot change
        if ( stickMath_lib.rand01() >= volatileRate)
            return true;

        while (true)
        {
            sum_deg = 0.0;
            degX = stickMath_lib.randDouble(-30.0, 30.0);
            degY = stickMath_lib.randDouble(-30.0, 30.0);
            degZ = stickMath_lib.randDouble(-30.0, 30.0);
            sum_deg = Math.abs(degX) + Math.abs(degY) + Math.abs(degZ);
            if (sum_deg >=30 && sum_deg <=60 )
                break;
        }

        this.finalRotation[0]+= degX;
        this.finalRotation[1]+= degY;
        this.finalRotation[2]+= degZ;
        System.out.println("new final rotation is " + finalRotation[0] + " " +
                finalRotation[1] + " " + finalRotation[2]);

        //apply this new rotation
        // Note, Important:::
        // Here the input param are degX, degY, degZ
        // rather than finalRotation[0, 1, 2]
        // It is because the angle we need to rotate is not from (0,0,0)
        // but we rotate relatively from a "already rotated position"

        //this.finalRotateAllPoints(degX, degY, degZ);
        //this.obj1.rotateMesh(finalRotation);

        return true;
    }


    /**
     *  Decide what is the best tube to center the shape at
     */
    private int findBestTubeToCenter()
    {
        boolean showDebug = false;
        int i, j, k, a,b;
        int maxTreeLevel = 1;
        int[] treeLevel = new int[nComponent+1];
        if ( showDebug)
        {
            System.out.println("recenter the shape):");
            System.out.println("nComp " + this.nComponent);
        }

        //1.decide the tree level
        this.decideLeafBranch();
        boolean[][] connect = new boolean[20][20];
        for (i = 1; i<= this.nJuncPt; i++)
          for (j=1; j<= JuncPt[i].nComp; j++)
            for (k=j+1; k<= JuncPt[i].nComp; k++)
            {
                a = JuncPt[i].comp[j];
                b = JuncPt[i].comp[k];
                connect[a][b] = true;
                connect[b][a] = true;
            }

        for (i=1; i<=nComponent;i ++)
        {
            if ( LeafBranch[i] == true)
                treeLevel[i] = 1;
            else
                treeLevel[i] = -1; //undetermined
        }

        // decide level2
        for (i=1; i<=nComponent; i++)
            if (treeLevel[i] == -1)
            {
                for (j=1; j<= nComponent; j++)
                    if ( connect[i][j] == true && treeLevel[j] == 1) // j is a neighbor tube
                    {
                        treeLevel[i] = 2;
                        maxTreeLevel = 2;
                    }
            }
        // decide level3
        for (i=1; i<=nComponent; i++)
            if (treeLevel[i] == -1)
            {
                for (j=1; j<= nComponent; j++)
                    if ( connect[i][j] == true && treeLevel[j] == 2) // j is a neighbor tube
                    {
                        treeLevel[i] = 3;
                        maxTreeLevel = 3;
                    }
            }
        // decide level4
        for (i=1; i<=nComponent; i++)
            if (treeLevel[i] == -1)
            {
                for (j=1; j<= nComponent; j++)
                    if ( connect[i][j] == true && treeLevel[j] == 3) // j is a neighbor tube
                    {
                        treeLevel[i] = 4;
                        maxTreeLevel = 4;
                    }
            }
        // not possible to have level 5 since we have only 8 tube at most
        if ( showDebug)
        {
            for (i=1; i<= nComponent; i++)
                System.out.println("tube " + i + " tree level " + treeLevel[i]);
        }
        // Choose one of the tube with highest tree level (i.e. it is torso)

        // find the mass center of the shape
        Point3d cMass = new Point3d();
        int totalVect = 0;
        for (i=1; i<=nComponent; i++)
        {
            totalVect += comp[i].nVect;
            for (j=1; j<= comp[i].nVect; j++)
                cMass.add(comp[i].vect_info[j]);
        }
        cMass.x /= totalVect;
        cMass.y /= totalVect;
        cMass.z /= totalVect;

        //this.globalCenterMass = cMass;

        //then, we can pick the shape (1.highest treeLevel, 2. near to cMass)
        int bestComp = -1;
        double bestDist = 1000000.0;
        Point3d newCenter = new Point3d();
        for (i=1; i<=nComponent; i++)
            if (treeLevel[i] == maxTreeLevel)
        {
                Point3d localMass = comp[i].mAxisInfo.mPts[ comp[i].mAxisInfo.branchPt];
                double dist = localMass.distance(cMass);
                if ( showDebug)
                    System.out.println("dist btw comp " + i  +"  with cMass is " + dist);
                if ( dist < bestDist)
                {
                    bestDist = dist;
                    bestComp = i;
                    newCenter = new Point3d( comp[i].mAxisInfo.mPts[26]);
                }

        }
        if ( showDebug)
        {
            System.out.println("The best tube to center is " + bestComp);
            System.out.println("new center pos" + newCenter);
        }
        return bestComp;
    }
    /**
     *   A function that will put the center of comp1 back to origin
    */
    private void centerShapeAtOrigin(int decidedCenterTube)
    {
        boolean showDebug = false;
        int i;
        int compToCenter = decidedCenterTube;
        if ( compToCenter == -1) // no preference
             compToCenter = this.findBestTubeToCenter();
        Point3d origin = new Point3d(0.0, 0.0, 0.0);

        this.nowCenterTube = compToCenter;
        //Point3d nowComp1Center =   new Point3d(comp[compToCenter].mAxisInfo.mPts[comp[compToCenter].mAxisInfo.branchPt]);
        // Dec 26th, change .branchPt to .MiddlePT (i.e. always at middle)
        int midPtIndex = 26;
        Point3d nowComp1Center =     new Point3d(comp[compToCenter].mAxisInfo.mPts[midPtIndex]);
        Vector3d shiftVec = new Vector3d();
        shiftVec.sub(origin, nowComp1Center);
//        System.out.println("comp to center "+ compToCenter);
//        System.out.println(nowComp1Center);
        if ( origin.distance(nowComp1Center) > 0.001)
        {
            if ( showDebug)
                System.out.println("shift to make it center at origin!");
            Point3d finalPos =new Point3d();

            for (i=1; i<= nComponent; i++)
            {
                finalPos.add( comp[i].mAxisInfo.transRotHis_finalPos, shiftVec);
                this.comp[i].translateComp( finalPos);
            }
            //also, all JuncPt and EndPt
            for (i=1; i<=nJuncPt; i++)
            {
                JuncPt[i].pos.add(shiftVec);
            }
            for (i=1; i<=nEndPt; i++)
            {
                endPt[i].pos.add(shiftVec);
            }
            //I'll call this check seperately
            //if ( this.validMStickSize() ==  false)
            //              return false;
        }
        //return true;

    }
    /**
        reAssign the junction radius value
        One of the last function call by mutate()
    */
    private void MutateSUB_reAssignJunctionRadius()
    {
        double rad_Volatile = 0.5;
        double nowRad, u_value;
        boolean showDebug = false;
        int try_time = 0;
        if ( showDebug)
            System.out.println("In radius reassign at junction");
        boolean[] radChgFlg = new boolean[ nComponent+1];
        int i, j;
        MatchStick old_mStick = new MatchStick();
        old_mStick.copyFrom(this); // a back up

        while (true)
        {
            // for all juncPt, we check the radius value is in the legal range,
            // if not, we must reassign,
            // if yes, there is certain probability we chg the assigned value
            for (i=1; i<= nJuncPt; i++)
            {

            double rMin = -10.0, rMax = 100000.0, tempX;
                    int nRelated_comp = JuncPt[i].nComp;
                    for (j = 1 ; j <= nRelated_comp; j++)
                {
                        rMin = Math.max( rMin, comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 10.0);
                        tempX = Math.min( 0.5 *comp[JuncPt[i].comp[j]].mAxisInfo.rad,
                        comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 3.0);
                        rMax = Math.min( rMax, tempX);
                }

                    if (rMax < rMin)
                            System.out.println(" In radius assign, ERROR: rMax < rMin");

            boolean haveChg = false;
            nowRad = -10.0;
            // Check now Junc.rad versus rMin, rMax
             if ( JuncPt[i].rad > rMax || JuncPt[i].rad < rMin)
            {
                haveChg = true; // definitely need to chg
                if (stickMath_lib.rand01() < rad_Volatile)
                    nowRad = stickMath_lib.randDouble( rMin, rMax);
                else // we don't want huge chg
                {
                    if ( JuncPt[i].rad > rMax)  nowRad = rMax;
                    if ( JuncPt[i].rad < rMin)  nowRad = rMin;
                }
            }
            else // the original value is in legal range
            {
                if (stickMath_lib.rand01() < rad_Volatile)
                {
                    haveChg = true;
                    while(true)
                    {
                        nowRad = stickMath_lib.randDouble( rMin, rMax);
                        double dist = Math.abs( nowRad - JuncPt[i].rad);
                        double range = rMax - rMin;
                        if ( dist >= 0.2 * range) break; // not very near the original value
                    }
                }

            }

                    // set the new value to each component
            if ( haveChg ) // the radius have been chged
            {
                JuncPt[i].rad = nowRad;
                for (j = 1 ; j <= nRelated_comp ; j++)
                    {
                    radChgFlg[ JuncPt[i].comp[j]] = true;
                    u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                    if ( Math.abs( u_value - 0.0) < 0.0001)
                    {
                        comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                        comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
                    }
                    else if ( Math.abs(u_value - 1.0) < 0.0001)
                    {
                        comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                        comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
                    }
                    else // middle u value
                    {
                        comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                        comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
                    }
                }
            }
                  } // for loop along JuncPt

            // now use new radius value to generate new tube
            boolean success = true;
            for (i=1; i<= nComponent; i++)
               if ( radChgFlg[i] == true)
               {
                if ( comp[i].RadApplied_Factory() == false)
                    success = false; // fail Jacob or gradR
               }
            if (success ) // then check closeHit & IntheBox
            {
                if ( this.validMStickSize() ==  false)
                    success = false;
                if ( this.finalTubeCollisionCheck() == true)
                    success = false;
            }

            if ( success )
                break; // not error, good
            else
            {
//                System.out.println("In rad reassign at junction: need re-try");
                this.copyFrom(old_mStick);
                for (i=1; i<=nComponent; i++)
                    radChgFlg[i] = false;
                try_time++;
            }
            if ( try_time > 30)
                break; //give up the junction change
        } // while loop
    }



    /**
        subFunction of: (replaceComponent, fineTuneComponent) <BR>
        Will determine the relation of each component to the target component
    */
    private int[] MutationSUB_compRelation2Target(int targetComp)
    {
        // 1. create connect map
        boolean[][] connect = new boolean[20][20];
        int i, j, k, a,b;
        for (i = 1; i<= this.nJuncPt; i++)
          for (j=1; j<= JuncPt[i].nComp; j++)
            for (k=j+1; k<= JuncPt[i].nComp; k++)
            {
                a = JuncPt[i].comp[j];
                b = JuncPt[i].comp[k];
                connect[a][b] = true;
                connect[b][a] = true;
            }

        int[] complabel = new int[nComponent+1];
        int startPt;
        for (startPt = 1; startPt <= nComponent; startPt++)
            if ( connect[startPt][targetComp] == true) // this startPt is directly connecto to targetComp
            {
                complabel[startPt] = startPt;
                //search out from startPt, but, can't pass over targetComp
                int[] visited = new int[nComponent+1];
                visited[startPt] = 1;
                boolean chgFlg;
                while (true)
                {
                    chgFlg = false;
                   for (i=1; i<= nComponent; i++)
                      if (visited[i] == 1)
                    {
                        for (j=1; j<=nComponent; j++)
                          if (connect[i][j] == true && j != targetComp && visited[j] == 0)
                          {
                            visited[j] = 1;
                            chgFlg = true;
                          }
                        visited[i] = 2;
                    }
                    if (chgFlg == false) break;
                }
                for (i=1; i<=nComponent; i++)
                   if ( visited[i] == 2)
                    complabel[i] = startPt;
            }
        return complabel;
    }

    /**
           subFunction of: (replaceComponent, fineTuneComponent) <BR>
        Will determine the radius of the modified component
        If there is value in [][] oriValue, it is the radius value of the original component
    */
        private void MutationSUB_radAssign2NewComp( int targetComp, double[][] oriValue)
    {
        boolean showDebug = false;
        int i, j;
        double rMin, rMax;
        double volatileRate = 0.7;
        double nowRad= -100.0, u_value;
        {
            i = targetComp;
            comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
            }

        //set old value at JuncPt
        for (i=1; i<=nJuncPt; i++)
        {
            for (j=1; j<= JuncPt[i].nComp; j++)
               if ( JuncPt[i].comp[j] == targetComp)
               {
                nowRad = JuncPt[i].rad;

                u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                        if ( Math.abs( u_value - 0.0) < 0.0001)
                {
                            comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                    comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
                }
                        else if ( Math.abs(u_value - 1.0) < 0.0001)
                {
                    comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                    comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
                }
                        else // middle u value
                {
                    comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                    comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
                }
               }
        }

        //set new value at end Pt
        for (i=1; i<= nEndPt; i++)
          if (endPt[i].comp == targetComp)
          {
            //update the information of this endPt, besides radius assignment
            Point3d newPos = new Point3d( comp[targetComp].mAxisInfo.mPts[ endPt[i].uNdx]);
            Vector3d newTangent = new Vector3d( comp[targetComp].mAxisInfo.mTangent[ endPt[i].uNdx]);
            if ( endPt[i].uNdx == 51)
                newTangent.negate();
            endPt[i].pos.set(newPos);
            endPt[i].tangent.set(newTangent);

            //set radius
            u_value = ((double)endPt[i].uNdx-1.0) / (51.0-1.0);
            int nowComp = targetComp;
            rMin = 0.00001; // as small as you like
                rMax = Math.min( comp[nowComp].mAxisInfo.arcLen / 3.0, 0.5 * comp[nowComp].mAxisInfo.rad);

            // retrive the oriValue
            double oriRad = -10.0;
            if ( endPt[i].uNdx == 1)
                oriRad = oriValue[0][1];
            else if ( endPt[i].uNdx == 51)
                oriRad = oriValue[2][1];

                // select a value btw rMin and rMax
            double range = rMax - rMin;
            if ( oriRad < 0.0)
                nowRad = stickMath_lib.randDouble( rMin, rMax);
            else // in the case where we have old value
            {
                if (stickMath_lib.rand01() < volatileRate)
                {
                      // gen a new similar value
                      while (true)
                      {
                      nowRad = stickMath_lib.randDouble( rMin, rMax);
                      if ( oriRad > rMax || oriRad < rMin)
                            break;
                      if ( Math.abs(nowRad - oriRad) >= 0.2* range && Math.abs(nowRad - oriRad) <= 0.4* range)
                        break;
                      }
                }
                else // keep same value if possible
                {
                    if ( oriRad <= rMax && oriRad >= rMin)
                        nowRad = oriRad;
                    else if ( oriRad > rMax)
                            nowRad = rMax;
                    else if ( oriRad < rMin)
                            nowRad = rMin;
                }
            }

                endPt[i].rad = nowRad;

                if ( Math.abs( u_value - 0.0) < 0.0001)
                {
                comp[nowComp].radInfo[0][0] = 0.0;
                comp[nowComp].radInfo[0][1] = nowRad;
                }
                else if (Math.abs(u_value - 1.0) < 0.0001)
                {
                comp[nowComp].radInfo[2][0] = 1.0;
                comp[nowComp].radInfo[2][1] = nowRad;
                        }
                else // middle u value
                    System.out.println( "error in endPt radius assignment");
          }

        //set intermediate pt if not assigned yet
          i = targetComp;
              if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
            {
                int branchPt = comp[i].mAxisInfo.branchPt;
                u_value = ((double)branchPt-1.0) / (51.0 -1.0);

                rMin = comp[i].mAxisInfo.arcLen / 10.0;
                rMax = Math.min(comp[i].mAxisInfo.arcLen / 3.0, 0.5 * comp[i].mAxisInfo.rad);
                // select a value btw rMin and rMax

                double oriRad = oriValue[1][1]; // the middle radius value
                double range = rMax - rMin;
                if ( oriRad < 0.0)
                    nowRad = stickMath_lib.randDouble( rMin, rMax);
                else // in the case where we have old value
                {

                    if (stickMath_lib.rand01() < volatileRate)
                    {
                        if ( showDebug)
                            System.out.println("gen similar in range" + rMin + " ~ " + rMax);
                          // gen a new similar value
                          while (true)
                          {
                          nowRad = stickMath_lib.randDouble( rMin, rMax);
                        if ( oriRad > rMax || oriRad < rMin)
                            break;
                        if ( Math.abs(nowRad - oriRad) >= 0.2* range && Math.abs(nowRad - oriRad) <= 0.4* range)
                            break;
                               }
                    }
                    else // keep same value if possible
                    {
                        if ( showDebug)
                            System.out.println("try to keep same in range" + rMin + " ~ "+ rMax);
                        if ( oriRad <= rMax && oriRad >= rMin)
                            nowRad = oriRad;
                        else if ( oriRad > rMax)
                            nowRad = rMax;
                        else if ( oriRad < rMin)
                            nowRad = rMin;

                    }
                    if ( showDebug)
                    {
                        System.out.println("In assign Rad, we have old value +" + oriRad);
                        System.out.println("and new vlaue is " + nowRad);
                    }
                }

                comp[i].radInfo[1][0] = u_value;
                comp[i].radInfo[1][1] = nowRad;
                }
    }
    /**
        subFunction of: (replaceComponent, fineTuneComponent) <BR>
        Will determine the Hinge Pt to stay still
    */
    private int MutationSUB_determineHinge(int targetComp)
    {
        int i, j;
        int nHingePt = 1, alignedPt= -100;
        int nowComp, uNdx;
        int[] HingePtNdx = new int[4];

        //special case, where there is only 1 tube remaining
        if ( this.nComponent ==1 )
            return 26; // use the center pt to perform as hinge
        for (i=1; i<= nJuncPt; i++)
            for (j=1; j<= JuncPt[i].nComp; j++)
            {
                nowComp = JuncPt[i].comp[j];
                uNdx = JuncPt[i].uNdx[j];
                if ( nowComp == targetComp)
                {
                    HingePtNdx[nHingePt] = uNdx;
                    nHingePt++;
                }
            }
        nHingePt--;
        // now nHingePt should be 1 ~ 3
        if (nHingePt == 1)
            alignedPt = HingePtNdx[1];
        else if ( nHingePt == 2)
        {
            double[] prob = { 0.5, 1.0};
            int Ndx = stickMath_lib.pickFromProbDist( prob);
            alignedPt = HingePtNdx[Ndx];
        }
        else if ( nHingePt == 3)
        {
            double[] prob = { 0.3333, 0.6666, 1.0};
            int Ndx = stickMath_lib.pickFromProbDist( prob);
            alignedPt = HingePtNdx[Ndx];
        }
        return alignedPt;
    }
    /**
        replace one of the compononent with a total new tube
    */
    private boolean replaceComponent(int id)
    {
        int i, j, k;
        int TotalTrialTime=0;
        int inner_totalTrialTime = 0; // for inner while loop
        boolean showDebug = false;
        //final double TangentSaveZone = Math.PI / 4.0;
        boolean[] JuncPtFlg = new boolean[nJuncPt+1]; // = true when this JuncPt is related to the (id) component
        int[] targetUNdx = new int[nJuncPt+1]; // to save the target uNdx in particular Junc pt
        if ( showDebug)
           System.out.println("In replace component, will replace comp " + id);
        // we'll find this function need to share some sub_function with fineTuneComponent
        // 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
        int alignedPt;
        alignedPt = MutationSUB_determineHinge( id);
        Point3d alignedPos = new Point3d();
        alignedPos.set( comp[id].mAxisInfo.mPts[alignedPt]);

        int[] compLabel = new int[nComponent+1];
        int TangentTryTimes = 1;
        compLabel = MutationSUB_compRelation2Target(id);

        //debug, show compLabel
        //System.out.println("compLabel: ");
        //for (i=1; i<= nComponent; i++)
        //  System.out.println("comp " + i + " with label" + compLabel[i]);
        //System.out.println("Hinge Pt is " + alignedPt);

        //2. start picking new MAxisArc
        for (i=1; i<= nJuncPt; i++)
            for (j=1; j<= JuncPt[i].nComp; j++)
            {
                if ( JuncPt[i].comp[j] == id)
                {
                    JuncPtFlg[i] = true;
                    targetUNdx[i] = JuncPt[i].uNdx[j];
                }
            }


        MAxisArc nowArc;
        MatchStick old_MStick = new MatchStick();
        old_MStick.copyFrom(this);
        while (true)
        {
           while(true)
           {
            while(true)
            {
               // store back to old condition
               this.copyFrom(old_MStick);
               // random get a new MAxisArc
                nowArc = new MAxisArc();
                nowArc.genArcRand();
                Vector3d finalTangent = new Vector3d();
                finalTangent = stickMath_lib.randomUnitVec();
                double devAngle = stickMath_lib.randDouble(0, Math.PI * 2);
                nowArc.transRotMAxis(alignedPt, alignedPos, alignedPt, finalTangent, devAngle);
                boolean tangentFlg = true;
                Vector3d nowTangent = new Vector3d();
                for (i=1; i<=nJuncPt; i++)
                  if ( JuncPtFlg[i] == true)
                  {
                    int uNdx = targetUNdx[i];
                    boolean midBranchFlg = false;
                    if (uNdx == 1)
                        finalTangent.set( nowArc.mTangent[uNdx]);
                    else if (uNdx == 51)
                    {
                        finalTangent.set( nowArc.mTangent[uNdx]);
                        finalTangent.negate();
                    }
                    else // middle branch Pt
                    {
                        midBranchFlg = true;
                        finalTangent.set( nowArc.mTangent[uNdx]);
                    }
                    // check the angle
                    for (j=1; j<= JuncPt[i].nTangent; j++)
                       if ( JuncPt[i].tangentOwner[j] != id) // don't need to check with the replaced self
                    {
                        nowTangent = JuncPt[i].tangent[j]; // soft copy is fine here
                        if ( nowTangent.angle(finalTangent) <= TangentSaveZone ) // angle btw the two tangent vector
                            tangentFlg = false;
                        if ( midBranchFlg == true)
                        {
                            finalTangent.negate();
                            if ( nowTangent.angle(finalTangent) <= TangentSaveZone ) //
                                tangentFlg = false;
                        }
                    }

                  } // for loop, check through related JuncPt for tangentSaveZone
                if (tangentFlg == true) // still valid after all tangent check
                    break;
                if ( TangentTryTimes > 100)
                    return false;
            } // third while, will quit after tangent Save Zone check passed



            //update the information of the related JuncPt
            Vector3d finalTangent = new Vector3d();
            for (i=1; i<= nJuncPt; i++)
              if (JuncPtFlg[i] == true)
            {
                int nowUNdx = targetUNdx[i];
                finalTangent.set( nowArc.mTangent[ nowUNdx]);
                if ( targetUNdx[i] == 51)
                    finalTangent.negate();
                Point3d newPos = nowArc.mPts[ nowUNdx];
                Point3d shiftVec = new Point3d();
                shiftVec.sub( newPos, JuncPt[i].pos);

                if ( nowUNdx != alignedPt) // not the aligned one, we need to translate
                {
                   for (j=1; j<= JuncPt[i].nComp; j++)
                    if ( JuncPt[i].comp[j] != id)
                    {
                        int nowCompNdx = JuncPt[i].comp[j];
                        for (k=1; k<= nComponent; k++)
                          if (compLabel[k] == nowCompNdx) // the one should move with nowCompNdx
                        {
                            int nowComp = k;
                            Point3d finalPos =new Point3d();
                            finalPos.add( comp[nowComp].mAxisInfo.transRotHis_finalPos, shiftVec);
                            if (showDebug)
                               System.out.println("we have translate comp " + nowComp + "by " + shiftVec);
                            this.comp[nowComp].translateComp( finalPos);
                            // translate the component
                        }
                    }
                }

                JuncPt[i].pos = newPos;
                //update the tangent information
                boolean secondFlg = false; // determine if the first or second tanget
                for ( j = 1; j <= JuncPt[i].nTangent; j++)
                {
                   if (JuncPt[i].tangentOwner[j] == id && secondFlg == false)
                   {
                    JuncPt[i].tangent[j].set(finalTangent);
                    secondFlg = true;
                   }
                   else if ( JuncPt[i].tangentOwner[j] == id && secondFlg == true)
                   {
                    finalTangent.negate();
                    JuncPt[i].tangent[j].set(finalTangent);
                   }
                }
            }
                // now, we can check skeleton closeness

            //set the component to its new role
            boolean branchUsed = this.comp[id].branchUsed;
            int connectType = this.comp[id].connectType;
            this.comp[id] = new TubeComp();
            this.comp[id].initSet( nowArc, branchUsed, connectType);
            boolean closeHit = this.checkSkeletonNearby( nComponent);
            if (closeHit == false) // a safe skeleton
                break;

            inner_totalTrialTime++;
            if ( inner_totalTrialTime > 25)
                return false;



           } // second while

            // update the info in end pt and JuncPt
            for (i=1; i<=nEndPt; i++)
            {
                Point3d newPos = new Point3d(  comp[ endPt[i].comp].mAxisInfo.mPts[ endPt[i].uNdx]);
                endPt[i].pos.set(newPos);
            }
            for (i=1; i<=nJuncPt; i++)
            {
                Point3d newPos = new Point3d( comp[JuncPt[i].comp[1]].mAxisInfo.mPts[ JuncPt[i].uNdx[1]]);
                JuncPt[i].pos.set(newPos);
            }
            // now, we apply radius, and then check skin closeness
            int radiusAssignChance = 5;
            int now_radChance = 1;
            boolean success_process = false;
            for (now_radChance = 1; now_radChance <= radiusAssignChance; now_radChance++)
            {
                // rad assign to new comp
                success_process = true;
                //show the radius value
//              System.out.println("rad assign: ");
//              comp[id].showRadiusInfo();
                double[][] fakeRadInfo = { {-10.0, -10.0}, {-10.0,-10.0}, {-10.0, -10.0}};
                this.MutationSUB_radAssign2NewComp(id, fakeRadInfo);
//                  comp[id].showRadiusInfo();
                if ( comp[id].RadApplied_Factory() == false)
                {
                    success_process = false;
                    continue; // not a good radius, try another
                }
                if ( this.validMStickSize() ==  false)
                {
                   if ( showDebug)
                    System.out.println("\n IN replace tube: FAIL the MStick size check ....\n");
                    success_process = false;
                }

                if ( this.finalTubeCollisionCheck() == true)
                {
                    if ( showDebug)
                    System.out.println("\n IN replace tube: FAIL the final Tube collsion Check ....\n");
                    success_process = false;
                }
                if ( success_process)
                    break;
            }

            TotalTrialTime++;
            if ( TotalTrialTime >5)
                return false;

            if ( success_process) // not be here, because of 5 times try
                break;

        } //outtest while

        if ( showDebug)
            System.out.println("successfully replace a tube");
        return true;
    }

    /**
        Fine tune the parameters of one of the component.
    */
    private boolean fineTuneComponent(int id)
    {
        int i, j, k;
        int inner_totalTrialTime = 0;
        int TotalTrialTime = 0; // the # have tried, if too many, just terminate
        final double volatileRate = 0.7;
        boolean showDebug = false;
        //final double TangentSaveZone = Math.PI / 4.0;
        boolean[] JuncPtFlg = new boolean[nJuncPt+1]; // = true when this JuncPt is related to the (id) component
        int[] targetUNdx = new int[nJuncPt+1]; // to save the target uNdx in particular Junc pt
        double[][] old_radInfo = new double[3][2];
        if ( showDebug)
            System.out.println("In fine tune component function, will fine tune comp " + id);

        // we'll find this function need to share some sub_function with fineTuneComponent
        // 1. determine alignedPt ( 3 possibilities, 2 ends and the branchPt)
        int alignedPt;
        alignedPt = MutationSUB_determineHinge( id);
//        Point3d alignedPos = new Point3d( comp[id].mAxisInfo.mPts[alignedPt]);

        int[] compLabel = new int[nComponent+1];
        int tangentTrialTimes = 0;
        compLabel = MutationSUB_compRelation2Target(id);

        //2. start picking new MAxisArc
        for (i=1; i<= nJuncPt; i++)
            for (j=1; j<= JuncPt[i].nComp; j++)
            {
                if ( JuncPt[i].comp[j] == id)
                {
                    JuncPtFlg[i] = true;
                    targetUNdx[i] = JuncPt[i].uNdx[j];
                }
            }
        for (i=0; i<3; i++)
            for (j=0; j<2; j++)
                old_radInfo[i][j] = comp[id].radInfo[i][j];

        MAxisArc nowArc;
        MatchStick old_MStick = new MatchStick();
        old_MStick.copyFrom(this);

        ///debug
        //tempStick = new MatchStick();
        //tempStick.copyFrom(old_MStick);

        while (true)
        {
           while(true)
           {
            while(true)
            {
               // store back to old condition
                tangentTrialTimes++;
               this.copyFrom(old_MStick);
               // random get a new MAxisArc
                nowArc = new MAxisArc();
                nowArc.genSimilarArc( this.comp[id].mAxisInfo, alignedPt,volatileRate);
                    // use this function to generate a similar arc

                Vector3d finalTangent = new Vector3d();


                boolean tangentFlg = true;
                Vector3d nowTangent = new Vector3d();
                for (i=1; i<=nJuncPt; i++)
                  if ( JuncPtFlg[i] == true)
                  {
                    int uNdx = targetUNdx[i];
                    boolean midBranchFlg = false;
                    if (uNdx == 1)
                        finalTangent.set( nowArc.mTangent[uNdx]);
                    else if (uNdx == 51)
                    {
                        finalTangent.set( nowArc.mTangent[uNdx]);
                        finalTangent.negate();
                    }
                    else // middle branch Pt
                    {
                        midBranchFlg = true;
                        finalTangent.set( nowArc.mTangent[uNdx]);
                    }
                    // check the angle
                    for (j=1; j<= JuncPt[i].nTangent; j++)
                       if ( JuncPt[i].tangentOwner[j] != id) // don't need to check with the replaced self
                    {
                        nowTangent = JuncPt[i].tangent[j]; // soft copy is fine here
                        if ( nowTangent.angle(finalTangent) <= TangentSaveZone ) // angle btw the two tangent vector
                            tangentFlg = false;
                        if ( midBranchFlg == true)
                        {
                            finalTangent.negate();
                            if ( nowTangent.angle(finalTangent) <= TangentSaveZone ) //
                                tangentFlg = false;
                        }
                    }

                  } // for loop, check through related JuncPt for tangentSaveZone
                if (tangentFlg == true) // still valid after all tangent check
                    break;
                else
                {

                    if ( showDebug)
                        System.out.println("didn't pass check tagent Zone in fine tune");
                }
                if (tangentTrialTimes > 100)
                    return false;
            } // third while, will quit after tangent Save Zone check passed



            //update the information of the related JuncPt
            Vector3d finalTangent = new Vector3d();
            for (i=1; i<= nJuncPt; i++)
              if (JuncPtFlg[i] == true)
            {
                int nowUNdx = targetUNdx[i];
                finalTangent.set( nowArc.mTangent[ nowUNdx]);
                if ( targetUNdx[i] == 51)
                    finalTangent.negate();
                Point3d newPos = nowArc.mPts[ nowUNdx];
                Point3d shiftVec = new Point3d();
                shiftVec.sub( newPos, JuncPt[i].pos);

                if ( nowUNdx != alignedPt) // not the aligned one, we need to translate
                {
                   for (j=1; j<= JuncPt[i].nComp; j++)
                    if ( JuncPt[i].comp[j] != id)
                    {
                        int nowCompNdx = JuncPt[i].comp[j];
                        for (k=1; k<= nComponent; k++)
                          if (compLabel[k] == nowCompNdx) // the one should move with nowCompNdx
                        {
                            int nowComp = k;
                            Point3d finalPos =new Point3d();
                            finalPos.add( comp[nowComp].mAxisInfo.transRotHis_finalPos, shiftVec);
                            if ( showDebug)
                                System.out.println("we have translate comp " + nowComp + "by " + shiftVec);
                            this.comp[nowComp].translateComp( finalPos);
                            // translate the component
                        }
                    }
                }

                JuncPt[i].pos = newPos;
                //update the tangent information
                boolean secondFlg = false; // determine if the first or second tanget
                for ( j = 1; j <= JuncPt[i].nTangent; j++)
                {
                   if (JuncPt[i].tangentOwner[j] == id && secondFlg == false)
                   {
                    JuncPt[i].tangent[j].set(finalTangent);
                    secondFlg = true;
                   }
                   else if ( JuncPt[i].tangentOwner[j] == id && secondFlg == true)
                   {
                    finalTangent.negate();
                    JuncPt[i].tangent[j].set(finalTangent);
                   }
                }
            }
                // now, we can check skeleton closeness

            //set the component to its new role
            boolean branchUsed = this.comp[id].branchUsed;
            int connectType = this.comp[id].connectType;
            this.comp[id] = new TubeComp();
            this.comp[id].initSet( nowArc, branchUsed, connectType);
            if (showDebug)
                System.out.println("In fine tune: tube to modify # " +id +" now check skeleton");
            boolean closeHit = this.checkSkeletonNearby( nComponent);
            if (closeHit == false) // a safe skeleton
            {
                break;
            }
            else
            {
                if ( showDebug)
                    System.out.println("skeleton check fail");
                // a debug check
//              this.copyFrom(old_MStick);
//              boolean newTest = this.checkSkeletonNearby(nComponent);
//              System.out.println("skeleton check result after recovery: " + newTest);
            }
            inner_totalTrialTime++;
            if ( inner_totalTrialTime > 25)
                return false;

           } // second while

            // update the info in end pt and JuncPt
            for (i=1; i<=nEndPt; i++)
            {
                Point3d newPos = new Point3d(  comp[ endPt[i].comp].mAxisInfo.mPts[ endPt[i].uNdx]);
                endPt[i].pos.set(newPos);
            }
            for (i=1; i<=nJuncPt; i++)
            {
                Point3d newPos = new Point3d( comp[JuncPt[i].comp[1]].mAxisInfo.mPts[ JuncPt[i].uNdx[1]]);
                JuncPt[i].pos.set(newPos);
            }
            // now, we apply radius, and then check skin closeness
            int radiusAssignChance = 5;
            int now_radChance = 1;
            boolean success_process = false;
            for (now_radChance = 1; now_radChance <= radiusAssignChance; now_radChance++)
            {
                // rad assign to new comp
                success_process = true;
                //show the radius value
                //System.out.println("rad assign: ");
                //comp[id].showRadiusInfo();
                this.MutationSUB_radAssign2NewComp(id, old_radInfo);
                //comp[id].showRadiusInfo();
                if ( comp[id].RadApplied_Factory() == false)
                {
                    success_process = false;
                    continue; // not a good radius, try another
                }
                if ( this.validMStickSize() ==  false)
                {
                  if ( showDebug)
                    System.out.println("\n IN replace tube: FAIL the MStick size check ....\n\n");
                    success_process = false;
                }

                if ( this.finalTubeCollisionCheck() == true)
                {
                   if ( showDebug)
                    System.out.println("\n IN replace tube: FAIL the final Tube collsion Check ....\n\n");
                    success_process = false;
                }
                if ( success_process)
                    break;
            }
            TotalTrialTime++;
            if ( TotalTrialTime >5)
                return false;
            if ( success_process) // not be here, because of 5 times try
                break;

        } //outtest while

        if ( showDebug)
            System.out.println("successfully fine tune a tube");
        return true;
    }

        /**
        function that add new tube in the mutation process
    */
    private boolean addTubeMutation(int nAddTube)
    {
        int add_trial = 0;
        boolean showDebug = false;
        if ( showDebug)
        {
            System.out.println("In Add tube mutation with  " + nAddTube +" components to add");
            System.out.println("Now nComp " + nComponent);
        }
        int i;

        for (i= nComponent+1; i<= nComponent+1 + nAddTube-1; i++)
            comp[i] = new TubeComp();

        // 1. sequentially adding new components

        int nowComp = this.nComponent+1;
        int old_nComp = this.nComponent;
        this.nComponent += nAddTube;
        double randNdx;
        boolean addSuccess;
         while (true)
        {
            if ( showDebug)
              System.out.println("TRY adding new MAxis on, now # " +  nowComp);
            randNdx = stickMath_lib.rand01();
            if (randNdx < PROB_addToEndorJunc)
            {
                if (nJuncPt == 0 || stickMath_lib.rand01() < PROB_addToEnd_notJunc)
                    addSuccess = this.Add_MStick(nowComp, 1);
                else
                    addSuccess = this.Add_MStick(nowComp, 2);
            }
            else
            {
                if (stickMath_lib.rand01() < PROB_addTiptoBranch)
                    addSuccess = this.Add_MStick(nowComp, 3);
                else
                    addSuccess = this.Add_MStick(nowComp, 4);
            }
            if (addSuccess == true) // otherwise, we'll runModeRun this while loop again, and re-generate this component
                nowComp ++;
            if (nowComp == this.nComponent+1)
                break;
            add_trial++;
            if ( add_trial > 100)
                return false;
          }

        //up to here, the eligible skeleton should be ready
        // 3. Assign the radius value
        this.RadiusAssign( old_nComp); // need to change this part

        // 4. Apply the radius value onto each component
//        boolean failSkin = false;
        for (i=old_nComp+1; i<= nComponent; i++)
        {
            if( this.comp[i].RadApplied_Factory() == false) // a fail application
            {
//               failSkin = true;
               return false;
            }
        }

        // 5. check if the final shape is not working ( collide after skin application)

        if ( this.validMStickSize() ==  false)
        {
             if ( showDebug)
            System.out.println("\n FAIL the MStick size check ....\n\n");
            return false;
        }
        if ( this.finalTubeCollisionCheck() == true)
        {
             if ( showDebug)
            System.out.println("\n FAIL the final Tube collsion Check ....\n\n");
            return false;
        }

        return true;

    }

    /**
        Remove the component from this shape ( the component to remove is indexed by removeFlg bool array
    */
    private void removeComponent(boolean[] removeFlg)
    {
        int i, j;
        int[] compMap = new int[20];
        boolean showDebug = false;
        if ( showDebug)
            System.out.println("In remove component sub.");
        // 1. generate the mapping from old comp to new comp
        int counter = 1, nRemove = 0;
        for (i=1; i<=nComponent; i++)
        {
           if (removeFlg[i] != true)
           {
            compMap[i] = counter;
            counter++;
           }
           else
            nRemove++;
        }

        // 2. go throuhg JuncPt, modify the related info
        for (i=1; i<= nJuncPt; i++)
        {
            JuncPt[i].removeComp( removeFlg);
        }

        // 3. check if some JuncPt reduced to EndPt
        for (i=1; i<=nJuncPt; i++)
          if (JuncPt[i].nComp == 1)
        {
            if (JuncPt[i].uNdx[1] == 1 || JuncPt[i].uNdx[1] == 51) // an end pt
            {
                //add a new endPt
                nEndPt++;
                this.endPt[nEndPt] = new EndPt_struct( JuncPt[i].comp[1], JuncPt[i].uNdx[1],
                    JuncPt[i].pos, JuncPt[i].tangent[1], JuncPt[i].rad );
            }
        }

        counter = 1;
        for (i=1; i<=nJuncPt; i++)
            if ( JuncPt[i].nComp > 1) // the one we want to keep
        {
            JuncPt[counter].copyFrom( JuncPt[i]);
            counter++;
        }
        nJuncPt = counter-1;

        // 4. check the endPt info update
        counter = 1;
        for (i=1; i<=nEndPt; i++)
            if (removeFlg[ endPt[i].comp] == false) // end Pt we want to hold
        {
            endPt[counter].copyFrom( endPt[i]);
            counter++;
        }
        nEndPt = counter -1;

        // 5. mapping the compoLabel to make the comp info in Junc and endPt correct

        for (i=1; i<= nComponent; i++)
            if ( compMap[i] !=0)
        {
            this.comp[ compMap[i]].copyFrom( comp[i]);
        }
        this.nComponent -= nRemove;

        //6. map the comp index at JuncPt and endPt to correct
        for (i=1; i<= nEndPt; i++)
        {
            endPt[i].comp = compMap[ endPt[i].comp];
        }
        for (i=1; i<= nJuncPt; i++)
        {
          for (j=1; j<= JuncPt[i].nComp; j++)
          {
            JuncPt[i].comp[j] = compMap[ JuncPt[i].comp[j]];
          }
          for (j=1; j<= JuncPt[i].nTangent; j++)
            JuncPt[i].tangentOwner[j] = compMap[ JuncPt[i].tangentOwner[j]];
        }

        //6. update the branchUsed information
        for (i=1; i<=nComponent; i++)
            comp[i].branchUsed = false; // reset to not used at first
        for (i=1; i<= nJuncPt; i++)
        {
            for (j=1; j<=JuncPt[i].nComp; j++)
              if (JuncPt[i].uNdx[j] != 1 && JuncPt[i].uNdx[j] != 51)
              {
                comp[i].branchUsed = true;
              }
        }
    }

    /**
        A private function that will decide which components are leaf branch, which are NOT
    */
    private void decideLeafBranch()
    {
        // the algorithm we use here is that:
        // regard the MStick as a un-directed connected graph ( with the connect adj matrix)
        // we sequentailly remove each stick, and see if the graph is still connected or not
        // if after removing a stick, the graph become un-connected, then this branch is a center branch
        // otherwise, it is a terminal branch
        boolean showDebug = false;
          //generate connection map
        boolean[][] connect = new boolean[20][20];
        int i, j, k, a,b;
        for (i = 1; i<= this.nJuncPt; i++)
          for (j=1; j<= JuncPt[i].nComp; j++)
            for (k=j+1; k<= JuncPt[i].nComp; k++)
            {
                a = JuncPt[i].comp[j];
                b = JuncPt[i].comp[k];
                connect[a][b] = true;
                connect[b][a] = true;
            }

        // now for each point, check connect, the result are saved in
        // boolean LeafBranch[]


        int nowNode, startPt, nVisited;
        for (nowNode = 1; nowNode <= nComponent; nowNode++)
        {
            boolean visited[] = new boolean[nComponent+1];
            if (nowNode == 1) startPt =2;
            else startPt = 1;
            visited[startPt] = true;
            nVisited = 1;

            boolean addnewFlg;
            while (true)
            {
                    addnewFlg = false;
                for (i=1; i<=nComponent; i++)
                    if (visited[i] == true)
                {
                    for (j=1; j<=nComponent; j++)
                    if (connect[i][j] && j != nowNode && visited[j] == false )
                    {
                        visited[j] = true;
                        nVisited++;
                        addnewFlg = true;
                    }

                }

                if ( nVisited == nComponent -1) // all point are reachable
                {
                    LeafBranch[nowNode] = true;
                    break;
                }

                        if (addnewFlg == false) // can't add more vertex, before we explore the whole graph
                    {
                    LeafBranch[nowNode] = false;
                    break;
                }

            }

        }

        //debug, show the connection
//      for (i=1; i<=nComponent; i++)
//      {
//          System.out.print(i +": ");
//          for (j=1; j<=nComponent; j++)
//              if (connect[i][j])
//                  System.out.print( "1 ");
//              else
//                  System.out.print( "0 ");
//          System.out.println("");
//      }
        //debug, show the branching information
        if ( showDebug)
        for (i=1; i<=nComponent; i++)
        {
            System.out.println("Tube " + i + " with branch index " + LeafBranch[i]);
        }

    }

    /*
     *   calculate the center position of the shape
     *   which can be used to calculate the relative x,y,z for others
     */
    public Point3d getMassCenter()
    {
        Point3d center = new Point3d(0,0,0);
//        Point3d center_v2 = new Point3d(0,0,0);
        int i;
        for (i=1; i<= obj1.nVect; i++)
        {
            center.x  += obj1.vect_info[i].x;
            center.y  += obj1.vect_info[i].y;
            center.z  += obj1.vect_info[i].z;
        }
        center.x /= obj1.nVect;
        center.y /= obj1.nVect;
        center.z /= obj1.nVect;
        // July 30 2009
        //there are two ways
        // 1. the avg of all points on the mesh
        // 2. the avg of all points on the mPts skeleton

        // I'll just try first one, and hope it do a good job

        /*
        for (i=1; i<= this.nComponent; i++)
        {
            for (j=1; j<= 51; j++)
            {
                    center_v2.x += this.comp[i].mAxisInfo.mPts[j].x;
                    center_v2.y += this.comp[i].mAxisInfo.mPts[j].y;
                    center_v2.z += this.comp[i].mAxisInfo.mPts[j].z;
            }
        }
        center_v2.x /= (51*nComponent);
        center_v2.y /= (51*nComponent);
        center_v2.z /= (51*nComponent);
        */

        //  System.out.println("In calculate the center...");
        //  System.out.println(center);
        //  System.out.println(center_v2);
        return center;
    }

    /**
     *   function that will change the position of medial axis points
     *   of all the components to the correct final positions.
     *   This function should only be called in the analysis
     *   (after the electrophysio exp...)
     */
    public void modifyMAxisFinalInfo()
    {
        //May 21st , I want to do the same
        // rotate, scale, and translateinZ for the components
        // (so, then, I have the correct 'final' (x,y,z) (tangent) info)

        // this change will only be applied, and then runModeRun data analysis
        // it should not runModeRun on shapes that we want to generate offsprings

        //we need to change (x,y,z) (tx,ty,tz) (r1,r2,r3)
        //  k and length, and the 'deviate angle'? (deviate angle no change?)
        int i,j;
//        double nowRot;
        double[] rotVec = new double[3];
            rotVec[0] = this.finalRotation[0];
            rotVec[1] = this.finalRotation[1];
            rotVec[2] = this.finalRotation[2];



        for (i=1; i<= this.nComponent; i++)
        {
            // 1. scale up the (r1,r2,r3), rad(1/k), and arcLen
            for (j=0; j<3; j++)
            {
                // comp[i].radInfo[j][0] should keep the same ( which is u index)
                  comp[i].radInfo[j][1] *= this.scaleForMAxisShape;
            }

            comp[i].mAxisInfo.arcLen *= this.scaleForMAxisShape;
            comp[i].mAxisInfo.rad *= this.scaleForMAxisShape;
            comp[i].mAxisInfo.curvature = 1.0 / comp[i].mAxisInfo.rad;
            //rotate and scale for finalPos
            // rotate and 'no' sclae for finalTangent


            // 1. rot X
            if ( rotVec[0] != 0.0)
            {
               Vector3d RotAxis = new Vector3d(1,0,0);
               double Angle = (rotVec[0] /180.0 ) *Math.PI;
               AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
               Transform3D transMat = new Transform3D();
               transMat.setRotation(axisInfo);

               for (j=1; j<=51; j++)
               {
                   transMat.transform(comp[i].mAxisInfo.mPts[j]);
                   transMat.transform(comp[i].mAxisInfo.mTangent[j]);
               }
               for (j=1; j<=comp[i].nVect; j++)
               {
                   transMat.transform(comp[i].vect_info[j]);
                   transMat.transform(comp[i].normMat_info[j]);
               }
               transMat.transform(comp[i].mAxisInfo.transRotHis_finalPos);
               transMat.transform(comp[i].mAxisInfo.transRotHis_finalTangent);

            }
            // 2. rot Y
            if ( rotVec[1] != 0.0)
            {
                   Vector3d RotAxis = new Vector3d(0,1,0);
                   double Angle = (rotVec[1] /180.0 ) *Math.PI;
                   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
                   Transform3D transMat = new Transform3D();
                   transMat.setRotation(axisInfo);

                   for (j=1; j<=51; j++)
                   {
                       transMat.transform(comp[i].mAxisInfo.mPts[j]);
                       transMat.transform(comp[i].mAxisInfo.mTangent[j]);
                   }
                   for (j=1; j<=comp[i].nVect; j++)
                   {
                       transMat.transform(comp[i].vect_info[j]);
                       transMat.transform(comp[i].normMat_info[j]);
                   }
                   transMat.transform(comp[i].mAxisInfo.transRotHis_finalPos);
                   transMat.transform(comp[i].mAxisInfo.transRotHis_finalTangent);

            }

            // 3. rot Z
            if ( rotVec[2] != 0.0)
            {
                   Vector3d RotAxis = new Vector3d(0,0,1);
                   double Angle = (rotVec[2] /180.0 ) *Math.PI;
                   AxisAngle4d axisInfo = new AxisAngle4d( RotAxis, Angle);
                   Transform3D transMat = new Transform3D();
                   transMat.setRotation(axisInfo);

                   for (j=1; j<=51; j++)
                   {
                       transMat.transform(comp[i].mAxisInfo.mPts[j]);
                       transMat.transform(comp[i].mAxisInfo.mTangent[j]);
                   }
                   for (j=1; j<=comp[i].nVect; j++)
                   {
                       transMat.transform(comp[i].vect_info[j]);
                       transMat.transform(comp[i].normMat_info[j]);
                   }
                   transMat.transform(comp[i].mAxisInfo.transRotHis_finalPos);
                   transMat.transform(comp[i].mAxisInfo.transRotHis_finalTangent);

            }

            for (j=0; j<=51; j++)
            {
                comp[i].mAxisInfo.mPts[j].scale(this.scaleForMAxisShape);
                comp[i].mAxisInfo.mPts[j].add(this.finalShiftinDepth);
            }

            for (j=1; j<=comp[i].nVect; j++)
            {
                comp[i].vect_info[j].scale(this.scaleForMAxisShape);
                comp[i].vect_info[j].add(finalShiftinDepth);
            }
            comp[i].mAxisInfo.transRotHis_finalPos.scale(this.scaleForMAxisShape);
            comp[i].mAxisInfo.transRotHis_finalPos.add(this.finalShiftinDepth);
            // no scale/add for the tangent, since it is a unit vector

            // don't change the devAngle
            //comp[i].mAxisInfo.transRotHis_devAngle =
        }




        // end of the change of component info



    }
    /**
        function that will merge all vect_info from each tube into one smooth, water-tight vect_info piece
    */

    public boolean smoothizeMStick()
    {
        int i;
        boolean showDebug =false;
//        boolean shiftOriginToSurface = true;
        MStickObj4Smooth[] MObj = new MStickObj4Smooth[nComponent+1];
        // 1. generate 1 tube Object for each TubeComp
//        System.out.println("we have n comp = " + nComponent);
        for (i=1; i<= nComponent; i++)
        {
            MObj[i] = new MStickObj4Smooth(this.comp[i]); // use constructor to do the initialization
        }

        if (nComponent == 1)
        {
            this.obj1 = MObj[1];
            return true;
        }

//        int[] facePerComp = new int[nComponent];

        // facePerComp[0] = MObj[1].nFac;
        //this.showConnect();

        // 2. Start adding tube by tube
        MStickObj4Smooth nowObj = MObj[1]; // use soft copy is fine here
        for (i=2; i<= nComponent; i++)
        {
            if ( showDebug)
                System.out.println("NOW merge comp " + i);

            int target = i;

            boolean res  = false;
            //if (i< 8)
                res = nowObj.objectMerge( MObj[target], false); // the nowObj will be updated to a object with new-added component
            //if (i== 8)
            //{
//              res = true;
//              //nowObj.fake_objectMerge( MObj[target]);
                //res = nowObj.objectMerge( MObj[target], true); // the nowObj will be updated to a object with new-added component

            //}
                    //nowObj.objectMerge( MObj[target], true); // the nowObj will be updated to a object with new-added component

                // facePerComp[i-1] = MObj[target].nFac;

            if (res == false)
                return false;
        }

//        for (i=1; i<= nComponent; i++) {
//        	facePerComp[i-1] = nowObj.comp[i].nFac;
//        }

        // 3. general smooth afterward
        nowObj.smoothVertexAndNormMat(6, 15); // smooth the vertex by 4 times. normal by 10times

        // for debug
        this.obj1 = new MStickObj4Smooth();
        this.obj1 = MObj[1];

//        this.obj1.facePerComp = facePerComp;
        // Oct 2nd 2008
        // At this point, origin ( fixation pt) is inside the first component
        // We, however, want the fixation point to be on the surface Pt.
        // so this is what we need to do.

        //debug, no rot now

        // this should already be the case but translate the shape to the origin?
        // only for random gen
//            this.obj1.translateVertexOnZ_ram();
//            this.obj1.translateToOrigin();


        this.obj1.rotateMesh(finalRotation);

        this.obj1.scaleTheObj(scaleForMAxisShape * externalSizeParam);

        this.finalShiftinDepth = this.obj1.translateVertexOnZ_ram();

//        this.finalShiftinDepth = new Point3d();
//        if ( shiftOriginToSurface) // a boolean
//            this.finalShiftinDepth = this.obj1.translateVertexOnZ(externalSizeParam);

//        System.out.println("depthshift: " + this.finalShiftinDepth.x + ", " + this.finalShiftinDepth.y + ", " + this.finalShiftinDepth.z);

        if (!doCenterShape) {
	        	// this.obj1.scaleTheObj(externalSizeParam);

	    		Point3d pt = new Point3d();
	    		pt.x = xyPosition.x;
	    		pt.y = xyPosition.y;
	    		pt.z = 0;
	    		obj1.translateBack(pt);

	//    		System.out.println("moving stim to " + pt.x + pt.y);
	    	}

        return true;
    }

    /**
         A simple function that switch the fix center to next branch
     */

    public void switchToWantedCenterTube()
    {
         int toCenter = this.nowCenterTube+1;
         if (toCenter > this.nComponent)
             toCenter = 1;
         System.out.println("new center tube: "+ toCenter);
         this.centerShapeAtOrigin(toCenter);
         if ( this.smoothizeMStick() ==  false)
         {
             System.out.println("FAIL smooth stick at switch center tube.");
             System.out.println("THIS SHOULD NOT HAPPEN6");
         }

    }

    public void switchToAimedCenterTube(int aimedTube)
    {
         int toCenter = aimedTube;
         System.out.println("new center tube: "+ toCenter);
         this.centerShapeAtOrigin(toCenter);
         if ( this.smoothizeMStick() ==  false)
         {
             System.out.println("FAIL smooth stick at switch center tube.");
             System.out.println("THIS SHOULD NOT HAPPEN7");
         }

    }

    /**
         A procedure that will change the radius profile of
         all the components into a particular fashion
     */
    public void changeRadProfile(int radType)
    {
        int i, j;

        System.out.println(" Try to do radChange type = " + radType);
        double mini_rad = 0.2;
        double fat_rad = 0.8;
//        double tip_head = 1.0, tip_body = 0.5, tip_end = 0.01;

//        double ball_body = 0.5, ball_end = 0.1;

        //we always want to assign at tips & center
        for (i=1; i<=nComponent; i++)
        {
            comp[i].radInfo[0][0] = 0.0;
            comp[i].radInfo[1][0] = 0.5;
            comp[i].radInfo[2][0] = 1.0;
        }

        // 1. try to make it all thin tubes
        /*
        if ( radType == 0 ) // regular tube with according width
        {
            for (i=1; i<= nComponent; i++)
            {
                double rMin, rMax;
                rMin = comp[i].mAxisInfo.arcLen/ 4.0;

                comp[i].radInfo[0][1] = rMin;
                comp[i].radInfo[1][1] = rMin;
                comp[i].radInfo[2][1] = rMin;
            }
        }
        */
        if (radType == 1) //thin stick
        {
            for (i=1 ;i<= nComponent; i++)
            {
                comp[i].radInfo[0][1] = mini_rad;
                comp[i].radInfo[1][1] = mini_rad;
                comp[i].radInfo[2][1] = mini_rad;
            }
        }
        else if ( radType == 2) //fat stick
        {
            for (i=1; i<= nComponent; i++)
            {
                comp[i].radInfo[0][1] = fat_rad;
                comp[i].radInfo[1][1] = fat_rad;
                comp[i].radInfo[2][1] = fat_rad;
            }
        }
        else if ( radType == 3) // tip away at end-point
        {
            double rMin, rMax;
            double nowRad, u_value;
            int try_times = 0;
            boolean retry;
             // 0. initialize to negative value
            while (true)
            {
                for (i= 1; i<=nComponent; i++)
                {
                    comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
                }
                // 1. assign at JuncPt
                for (i=1; i<=nJuncPt; i++)
                {
                        int nRelated_comp = JuncPt[i].nComp;
                        nowRad = 0.6 - 0.05 *try_times; // a strict value
                        if ( i== 1)
                            System.out.println("type == 3, retry , nowRad " + nowRad);
                         // assign the value to each component
                        JuncPt[i].rad = nowRad;

                         for (j = 1 ; j <= nRelated_comp ; j++)
                         {
                             u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                             if ( Math.abs( u_value - 0.0) < 0.0001)
                             {
                                 comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                                 comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
                             }
                             else if ( Math.abs(u_value - 1.0) < 0.0001)
                             {
                                 comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                                 comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
                             }
                             else // middle u value
                             {
                                 comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                                 comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
                             }

                         }
            } // loop nJuncPt

            // 2. assign at endPt
            for ( i = 1 ;  i <= nEndPt ; i++)
            {

                    int nowComp = endPt[i].comp;
                    u_value = ((double)endPt[i].uNdx -1.0 ) / (51.0 -1.0);

                nowRad = 0.00001;
                endPt[i].rad = nowRad;

                if ( Math.abs( u_value - 0.0) < 0.0001)
                {
                    comp[nowComp].radInfo[0][0] = 0.0;
                    comp[nowComp].radInfo[0][1] = nowRad;
                }
                else if (Math.abs(u_value - 1.0) < 0.0001)
                {
                    comp[nowComp].radInfo[2][0] = 1.0;
                    comp[nowComp].radInfo[2][1] = nowRad;
                 }
            }
            // 3. other middle Pt
              for ( i = 1 ; i <= nComponent ; i++)
                  if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
                  {
                    int branchPt = comp[i].mAxisInfo.branchPt;
                    u_value = ((double)branchPt-1.0) / (51.0 -1.0);

                    rMin = comp[i].mAxisInfo.arcLen / 10.0;
                    rMax = Math.min(comp[i].mAxisInfo.arcLen / 3.0, 0.5 * comp[i].mAxisInfo.rad);
                    nowRad = stickMath_lib.randDouble( rMin, rMax);
                    nowRad = 0.5* (comp[i].radInfo[0][1] + comp[i].radInfo[2][1] );
                    comp[i].radInfo[1][0] = u_value;
                    comp[i].radInfo[1][1] = nowRad;
                    }

                retry = false;
                for (i=1; i<=nComponent; i++)
                    if ( comp[i].RadApplied_Factory() == false)
                        retry = true;
                try_times++;
                if ( retry == false) break;


            } // while loop

        }
        else if ( radType == 4) // balloon dog
        {
            boolean retry;
            int try_times = 0;
            while (true)
            {
                System.out.println("radType = 4, try time" + try_times);
                for (i=1; i<=nComponent; i++)
                {
                    double rMin, rMax;
                    rMin = comp[i].mAxisInfo.arcLen/ 10.0;
                    rMax =  Math.min( 0.5 *comp[i].mAxisInfo.rad,
                             comp[i].mAxisInfo.arcLen / 3.0);
                    rMin = 0.2;
                    rMax = 0.9 - try_times * 0.1;
                    comp[i].radInfo[0][1] = rMin;
                    comp[i].radInfo[1][1] = rMax;
                    comp[i].radInfo[2][1] = rMin;

                    //comp[i].radInfo[0][1] = ball_end;
                    //comp[i].radInfo[1][1] = ball_body;
                    //comp[i].radInfo[2][1] = ball_end;

                    // immediately try to apply the rad, if fail, try some
                    // conservative values

                }
                retry = false;
                for (i=1; i<=nComponent; i++)
                    if ( comp[i].RadApplied_Factory() == false)
                        retry = true;
                try_times++;
                if ( retry == false) break;
            } // while loop
        }
        else if ( radType == 5) // opposite of balloon dog, dumbbell
        {
            boolean retry;
            int try_times = 0;
            while (true)
            {
                System.out.println("radType = 5, try time" + try_times);
                double rMin = 0.3;
                double rMax = 1.1 - try_times * 0.1;
                System.out.println("rMin, rmax: " + rMin + " " + rMax);
                for (i=1; i<=nComponent; i++)
                {
                    comp[i].radInfo[0][1] = rMax;
                    comp[i].radInfo[1][1] = rMin;
                    comp[i].radInfo[2][1] = rMax;
                }
                retry = false;
                for (i=1; i<=nComponent; i++)
                    if ( comp[i].RadApplied_Factory() == false)
                        retry = true;
                try_times++;
                if ( retry == false) break;
            } // while loop

        }
        else if ( radType == 6) // opposite of tip-away
        {
            double rMin, rMax;
            double nowRad, u_value, tempX;
            boolean retry;
            int try_times =0;
            while (true)
            {
                System.out.println("radType 6, retry " + try_times);
                // 0. initialize to negative value

                for (i= 1; i<=nComponent; i++)
                {
                    comp[i].radInfo[0][1] = -10.0; comp[i].radInfo[1][1] = -10.0; comp[i].radInfo[2][1] = -10.0;
                }
                // 1. assign at JuncPt
                for (i=1; i<=nJuncPt; i++)
                {
                    rMin = -10.0; rMax = 100000.0;
                    int nRelated_comp = JuncPt[i].nComp;
                    for (j = 1 ; j <= nRelated_comp; j++)
                    {
                            rMin = Math.max( rMin, comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 10.0);
                            tempX = Math.min( 0.5 *comp[JuncPt[i].comp[j]].mAxisInfo.rad,
                                    comp[JuncPt[i].comp[j]].mAxisInfo.arcLen / 3.0);
                            rMax = Math.min( rMax, tempX);
                    }

                         // select a value btw rMin and rMax

                     //nowRad = rMax;
                     nowRad = 0.2;
                         // assign the value to each component
                     JuncPt[i].rad = nowRad;

                         for (j = 1 ; j <= nRelated_comp ; j++)
                         {
                             u_value = ((double)JuncPt[i].uNdx[j]-1.0) / (51.0-1.0);
                             if ( Math.abs( u_value - 0.0) < 0.0001)
                             {
                                 comp[JuncPt[i].comp[j]].radInfo[0][0] = 0.0;
                                 comp[JuncPt[i].comp[j]].radInfo[0][1] = nowRad;
                             }
                             else if ( Math.abs(u_value - 1.0) < 0.0001)
                             {
                                 comp[JuncPt[i].comp[j]].radInfo[2][0] = 1.0;
                                 comp[JuncPt[i].comp[j]].radInfo[2][1] = nowRad;
                             }
                             else // middle u value
                             {
                                 comp[JuncPt[i].comp[j]].radInfo[1][0] = u_value;
                                 comp[JuncPt[i].comp[j]].radInfo[1][1] = nowRad;
                             }

                         }
            } // loop nJuncPt

            // 2. assign at endPt
            for ( i = 1 ;  i <= nEndPt ; i++)
            {

                    int nowComp = endPt[i].comp;
                    u_value = ((double)endPt[i].uNdx -1.0 ) / (51.0 -1.0);

                nowRad = 0.7 - 0.05 * try_times;
                endPt[i].rad = nowRad;

                if ( Math.abs( u_value - 0.0) < 0.0001)
                {
                    comp[nowComp].radInfo[0][0] = 0.0;
                    comp[nowComp].radInfo[0][1] = nowRad;
                }
                else if (Math.abs(u_value - 1.0) < 0.0001)
                {
                    comp[nowComp].radInfo[2][0] = 1.0;
                    comp[nowComp].radInfo[2][1] = nowRad;
                 }
            }
            // 3. other middle Pt
              for ( i = 1 ; i <= nComponent ; i++)
                  if ( comp[i].radInfo[1][1] == -10.0 ) // this component need a intermediate value
                  {
                    int branchPt = comp[i].mAxisInfo.branchPt;
                    u_value = ((double)branchPt-1.0) / (51.0 -1.0);

                    rMin = comp[i].mAxisInfo.arcLen / 10.0;
                    rMax = Math.min(comp[i].mAxisInfo.arcLen / 3.0, 0.5 * comp[i].mAxisInfo.rad);
                    nowRad = stickMath_lib.randDouble( rMin, rMax);
                    nowRad = 0.5* (comp[i].radInfo[0][1] + comp[i].radInfo[2][1] );
                    comp[i].radInfo[1][0] = u_value;
                    comp[i].radInfo[1][1] = nowRad;
                    }

              // 4. modification for tubes that have double endPt
              for (i=1; i<= nComponent; i++)
              {
                  int nowCount = 0;
                  for (j=1; j<= nEndPt; j++)
                      if (endPt[j].comp == i)
                          nowCount ++;

                  if ( nowCount == 2) // double end-ed
                  {
                      System.out.println("tube " + i + " is double float end");
                      comp[i].radInfo[1][1] =  comp[i].radInfo[0][1] / 2.0;

                  }
              }
                retry = false;
                for (i=1; i<=nComponent; i++)
                    if ( comp[i].RadApplied_Factory() == false)
                    {
                        retry = true;
                        System.out.println("tube " + i + " error ");
                    }
                try_times++;
                if ( retry == false) break;


            } // while loop


        }

        for (i=1; i<= nComponent; i++)
        {
            if ( comp[i].RadApplied_Factory() == false)
            {
                System.out.println("ERROR: this rad profile not work! at comp " + i);
            }
        }


        // do a fake Smooth, (no smooth at all)
        // but we want to have the scale and rotation and translation

        this.fake_smoothizeMStick();

    }

    /**
     *   This is for work for the radius Profile change only
     *   We want to scale & rotate the shape, but we don't need
     *   the smooth procedure at all
     */
    private void fake_smoothizeMStick()
    {
        int i;
        boolean showDebug = false;
        boolean shiftOriginToSurface = true;
        MStickObj4Smooth[] MObj = new MStickObj4Smooth[nComponent+1];
        // 1. generate 1 tube Object for each TubeComp
        for (i=1; i<= nComponent; i++)
        {
            MObj[i] = new MStickObj4Smooth(this.comp[i]); // use constructor to do the initialization
        }

        //this.showConnect();

        // 2. Start adding tube by tube
        MStickObj4Smooth nowObj = MObj[1]; // use soft copy is fine here
        for (i=2; i<= nComponent; i++)
        {
            if ( showDebug)
                System.out.println("NOW merge comp " + i);
            nowObj.fake_objectMerge( MObj[i]);

        }

        // for debug
        this.obj1 = new MStickObj4Smooth();
        this.obj1 = MObj[1];

        // Oct 2nd 2008
        // At this point, origin ( fixation pt) is inside the first component
        // We, however, want the fixation point to be on the surface Pt.
        // so this is what we need to do.

        //debug, no rot now
        this.obj1.rotateMesh(finalRotation);

        this.obj1.scaleTheObj(scaleForMAxisShape * externalSizeParam);
        // then, we don't need to call rotateMesh in other place at all

//        this.finalShiftinDepth = new Point3d();
//
//        if ( shiftOriginToSurface) // a boolean
//            this.finalShiftinDepth = this.obj1.translateVertexOnZ(scaleForMAxisShape);

        this.finalShiftinDepth = this.obj1.translateVertexOnZ_ram();

//        this.finalShiftinDepth = new Point3d();
//        if ( shiftOriginToSurface) // a boolean
//            this.finalShiftinDepth = this.obj1.translateVertexOnZ(externalSizeParam);

//        System.out.println("depthshift: " + this.finalShiftinDepth.x + ", " + this.finalShiftinDepth.y + ", " + this.finalShiftinDepth.z);

        if (!doCenterShape) {
	        	// this.obj1.scaleTheObj(externalSizeParam);

	    		Point3d pt = new Point3d();
	    		pt.x = xyPosition.x;
	    		pt.y = xyPosition.y;
	    		pt.z = 0;
	    		obj1.translateBack(pt);

        }

    }

    public void setXyPos(MyPoint xy) {
    	this.xyPosition = xy;
    }

    public void setExternalSize(double size){
    	this.externalSizeParam = size;
    }

    public void setDoCenterShape(boolean doCenter) {
    	this.doCenterShape = doCenter;
    }

    public void setTexSpec(ArrayList<Coordinates2D> texSpec) {
		this.texSpec = texSpec;
	}
    public void setTexFaceSpec(ArrayList<Point3d> texFaceSpec) {
		this.texFaceSpec = texFaceSpec;
	}

    public void setDoClouds(boolean doClouds) {
        this.doClouds = doClouds;
    }

    public void setViewport(int viewport) {
        this.viewport = viewport;
    }

    public void setFrameNum(int frameNum) {
        this.frameNum = frameNum;
    }

	public void setLowPass(boolean lowPass) {
		this.doLowPass = lowPass;
	}
	public boolean getLowPass() {
		return this.doLowPass;
	}

    protected void redraw_clouds() {
    	if (!alreadyClouded) {
	        // get bounding box
	        int[] stimBox = getStimBox();
	        minX  = stimBox[0]; minY  = stimBox[1];
	        nPixX = stimBox[2]; nPixY = stimBox[3];

//	        GL11.glBegin(GL11.GL_LINE_LOOP);
//	        	GL11.glVertex2d(boundingBox[0].x, boundingBox[0].y);
//	        	GL11.glVertex2d(boundingBox[0].x, boundingBox[1].y);
//	        	GL11.glVertex2d(boundingBox[1].x, boundingBox[1].y);
//	        	GL11.glVertex2d(boundingBox[1].x, boundingBox[0].y);
//	        GL11.glEnd();

	        int[] colors = new int[]{GL11.GL_RED,GL11.GL_GREEN,GL11.GL_BLUE};

	    	 // generate random matrix
	    	double[][] randPixels = genRandMatrix(nPixX,nPixY*2);

	    	List<double[][]> finalMatrix = new ArrayList<double[][]>();

	    	GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT, 1);

	    	for (int i=0; i<3; i++) {
		        // read from frame buffer
		        ByteBuffer redPixels = ByteBuffer.allocateDirect(nPixX*nPixY);
		        GL11.glReadPixels(minX, minY, nPixX, nPixY,colors[i], GL11.GL_UNSIGNED_BYTE, redPixels);

		        // convert to matrix
		        double[][] orig_pixels = byteBufferToComplexMatrix(redPixels,nPixX,nPixY);
		        double[][] pixels = normalizeBackground(orig_pixels,nPixX,nPixY);

		        // do fft of image
		        DoubleFFT_2D fftOfShape = new DoubleFFT_2D(nPixX,nPixY);
		        fftOfShape.complexForward(pixels);
		        ComplexMatrix shapeMatrix = new ComplexMatrix(nPixX,nPixY,pixels);

		        // do fft of random image
		        DoubleFFT_2D fftOfRand = new DoubleFFT_2D(nPixX,nPixY);
		        fftOfRand.complexForward(randPixels);
		        ComplexMatrix randMatrix = new ComplexMatrix(nPixX,nPixY,randPixels);

		        // add random phase to image phase
		        shapeMatrix.addPhase(randMatrix.getPhase());

		        // do ifft with scrambled phase
		        double[][] matrixForIfft = shapeMatrix.getRealImag();
		        DoubleFFT_2D inv_fftOfShape = new DoubleFFT_2D(nPixX,nPixY);
		        inv_fftOfShape.complexInverse(matrixForIfft,true);

		        finalMatrix.add(matrixForIfft);
	        }

	        // get pixels to write to frame buffer
	        ByteBuffer allPixels = ByteBuffer.allocateDirect(nPixX*nPixY*4);
	        GL11.glReadPixels(minX, minY, nPixX, nPixY, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, allPixels);

	        // get byte buffer to write
	        pixelsToWrite = getByteBufferToWrite(finalMatrix,allPixels,nPixX,nPixY);
    	}
    	// write byte buffer to framebuffer
//        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
//        GL11.glClearColor(0.5f, 0.5f, 0.5f, 0f);
//    	GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
    	if (isScreenInverted)
    		GL11.glRasterPos2d(boundingBox[1].x, boundingBox[0].y);
    	else
    		GL11.glRasterPos2d(boundingBox[0].x, boundingBox[0].y);
        GL11.glDrawPixels(nPixX, nPixY, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, pixelsToWrite);

        alreadyClouded = true;
    }

    protected void redraw_lowPass() {
    	if (!alreadyLowPassed) {
	        // get bounding box
	        int[] stimBox = getStimBox();
	        minX  = stimBox[0]; minY  = stimBox[1];
	        nPixX = stimBox[2]; nPixY = stimBox[3];

//	        GL11.glBegin(GL11.GL_LINE_LOOP);
//	        	GL11.glVertex2d(boundingBox[0].x, boundingBox[0].y);
//	        	GL11.glVertex2d(boundingBox[0].x, boundingBox[1].y);
//	        	GL11.glVertex2d(boundingBox[1].x, boundingBox[1].y);
//	        	GL11.glVertex2d(boundingBox[1].x, boundingBox[0].y);
//	        GL11.glEnd();

	        // read from frame buffer
	        GL11.glPixelStorei(GL11.GL_PACK_ALIGNMENT, 1);
	        ByteBuffer redPixels = ByteBuffer.allocateDirect(nPixX*nPixY);
	        GL11.glReadPixels(minX, minY, nPixX, nPixY, GL11.GL_RED, GL11.GL_UNSIGNED_BYTE, redPixels);

	        // convert to matrix
	        double[][] orig_pixels = byteBufferToComplexMatrix(redPixels,nPixX,nPixY);
	        double[][] pixels = normalizeBackground(orig_pixels,nPixX,nPixY);

	        // generate random matrix
	        double[][] randPixels = genRandMatrix(nPixX,nPixY*2);

	        // do fft of image
	        DoubleFFT_2D fftOfShape = new DoubleFFT_2D(nPixX,nPixY);
	        fftOfShape.complexForward(pixels);
	        ComplexMatrix shapeMatrix = new ComplexMatrix(nPixX,nPixY,pixels);

	        // do fft of random image
	        DoubleFFT_2D fftOfRand = new DoubleFFT_2D(nPixX,nPixY);
	        fftOfRand.complexForward(randPixels);
	        ComplexMatrix randMatrix = new ComplexMatrix(nPixX,nPixY,randPixels);

	        // add random phase to image phase
	        shapeMatrix.addPhase(randMatrix.getPhase());

	        // do ifft with scrambled phase
	        double[][] matrixForIfft = shapeMatrix.getRealImag();
	        DoubleFFT_2D inv_fftOfShape = new DoubleFFT_2D(nPixX,nPixY);
	        inv_fftOfShape.complexInverse(matrixForIfft,true);

	        // get pixels to write to frame buffer
	        ByteBuffer allPixels = ByteBuffer.allocateDirect(nPixX*nPixY*4);
	        GL11.glReadPixels(minX, minY, nPixX, nPixY, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, allPixels);

	        // get byte buffer to write
//	        pixelsToWrite = getByteBufferToWrite(matrixForIfft,allPixels,nPixX,nPixY);
    	}
    	// write byte buffer to framebuffer
//        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
//        GL11.glClearColor(0.5f, 0.5f, 0.5f, 0f);
//    	GL11.glClear(GL11.GL_COLOR_BUFFER_BIT);
    	if (isScreenInverted)
    		GL11.glRasterPos2d(boundingBox[1].x, boundingBox[0].y);
    	else
    		GL11.glRasterPos2d(boundingBox[0].x, boundingBox[0].y);
        GL11.glDrawPixels(nPixX, nPixY, GL11.GL_RGBA, GL11.GL_UNSIGNED_BYTE, pixelsToWrite);

        alreadyLowPassed = true;
    }

    private ByteBuffer getByteBufferToWrite(List<double[][]> complexMatrixToWrite, ByteBuffer allPixels, int nx, int ny) {
        ByteBuffer modifiedPixels = ByteBuffer.allocateDirect(nx*ny*4);
        allPixels.rewind();

        for(int i=0; i<ny; i++) {
            for (int j=0; j<nx; j++) {
                byte r = allPixels.get();
                byte g = allPixels.get();
                byte b = allPixels.get();
                int  a = allPixels.get() & 0xff;

                if ((r & 0xff) == 76 && (g & 0xff) == 76 && (b & 0xff) == 76) {
//            	if ((r & 0xff) == (g & 0xff) && (r & 0xff) == (b & 0xff)) {
                // if (a == 0) {
            		modifiedPixels.put(r);
                    modifiedPixels.put(g);
                    modifiedPixels.put(b);
                    modifiedPixels.put((byte)0);

                } else {
                	int red = (int)(complexMatrixToWrite.get(0)[j][2*i]);
		        	int green = (int)(complexMatrixToWrite.get(1)[j][2*i]);
		        	int blue = (int)(complexMatrixToWrite.get(2)[j][2*i]);
		        	modifiedPixels.put((byte)red);
		        	modifiedPixels.put((byte)green);
		        	modifiedPixels.put((byte)blue);
		        	modifiedPixels.put((byte)0);
                }

            }
        }

        modifiedPixels.rewind();
        return modifiedPixels;
    }

    private double[][] normalizeBackground(double[][] orig_pixels, int nx, int ny) {
        double[][] pixels = new double[nx][2*ny];

        double nPix = 0;
        double pix = 0;

        for(int i=0; i<nx; i++)
            for (int j=0; j<2*ny; j+=2)
                if (orig_pixels[i][j] != 127) {
                    pix += orig_pixels[i][j];
                    nPix++;
                }

        double newBackground = pix/nPix;

        for(int i=0; i<nx; i++)
            for (int j=0; j<2*ny; j+=2) {
                pixels[i][j+1] = 0;

                if (orig_pixels[i][j] == 127)
                    pixels[i][j] = newBackground;
                else
                    pixels[i][j] = orig_pixels[i][j];
            }

        return pixels;
    }

    private double[][] genRandMatrix(int nPixX, int nPixY) {
        double[][] randMatrix = new double[nPixX][nPixY];
        for (int i=0; i<nPixX; i++)
            for (int j=0; j<nPixY; j++)
                randMatrix[i][j] = Math.random();
        return randMatrix;
    }

    private int[] getStimBox() {
        ByteBuffer viewport_byte = ByteBuffer.allocateDirect(16 * 4);
        viewport_byte.order(ByteOrder.LITTLE_ENDIAN);
        IntBuffer viewport = viewport_byte.asIntBuffer();
        GL11.glGetInteger(GL11.GL_VIEWPORT, viewport);

        ByteBuffer modelview_byte = ByteBuffer.allocateDirect(16 * 4);
        modelview_byte.order(ByteOrder.LITTLE_ENDIAN);
        FloatBuffer modelview = modelview_byte.asFloatBuffer();
        GL11.glGetFloat( GL11.GL_MODELVIEW_MATRIX, modelview );

        ByteBuffer projection_byte = ByteBuffer.allocateDirect(16 * 4);
        projection_byte.order(ByteOrder.LITTLE_ENDIAN);
        FloatBuffer projection = projection_byte.asFloatBuffer();
        GL11.glGetFloat( GL11.GL_PROJECTION_MATRIX, projection );

        FloatBuffer minPos = FloatBuffer.allocate(3);
        GLU.gluProject((float)boundingBox[0].x,(float)boundingBox[0].y,0.0f,modelview,projection,viewport,minPos);

        FloatBuffer maxPos = FloatBuffer.allocate(3);
        GLU.gluProject((float)boundingBox[1].x,(float)boundingBox[1].y,0.0f,modelview,projection,viewport,maxPos);

        int xLim1 = (int)minPos.get(0);
        int yLim1 = (int)minPos.get(1);

        int xLim2 = (int)maxPos.get(0);
        int yLim2 = (int)maxPos.get(1);

        int minX = Math.min(xLim1, xLim2);
        int maxX = Math.max(xLim1, xLim2);
        int minY = Math.min(yLim1, yLim2);
        int maxY = Math.max(yLim1, yLim2);

        int nPixX = maxX - minX;
        int nPixY = maxY - minY;

        int[] stimBox = {minX, minY, nPixX, nPixY};
        return stimBox;
    }

    private double[][] byteBufferToComplexMatrix(ByteBuffer color, int nPixX, int nPixY) {
        double[][] pixels = new double[nPixX][2*nPixY];
        color.rewind();

        for(int i=0; i<nPixY; i++) {
            for (int j=0; j<nPixX; j++) {
                int a = color.get() & 0xff;
                pixels[j][2*i] = a;
                pixels[j][2*i + 1] = 0;
            }
        }
        return pixels;
    }

    public void setScreenInverted(boolean inverted) {
    	this.isScreenInverted = inverted;
    }
} //end of class

class EndPt_struct
{
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

//        int i;
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
class JuncPt_struct
{
      public int nComp, nTangent;
      public int[] comp = new int[20];
      public int[] uNdx = new int[20];
      public Point3d pos = new Point3d();
      public Vector3d[] tangent = new Vector3d[20];
      public int[] tangentOwner = new int[20];
      public double rad;

      public JuncPt_struct()
      {
        int i;
        for (i=1; i<20; i++)
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
        for (i=1; i<20; i++)
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
