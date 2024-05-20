package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.EndPt_struct;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.*;
import java.util.function.Predicate;

/**
 * MatchSticks that are used to generate stimuli for the GA Experiment.
 * Includes:
 * 1. Morphing
 * 2. Checking if the shape is inside the Receptive Field partially or completely
 *
 */
public class GAMatchStick extends MorphedMatchStick {

    ReceptiveField rf;


    public GAMatchStick(ReceptiveField rf, RFStrategy rfStrategy, String textureType) {
        this.rf = rf;
        this.rfStrategy = rfStrategy;
        this.textureType = textureType;
    }


    public GAMatchStick() {
    }


    @Override
    public void genMatchStickRand() {
        int nComp;
        int maxAttempts = 10;

        //Outer loop, wille change nComp until we find a shape that fits the RF
        while (true) {

            double[] nCompDist = getPARAM_nCompDist();
            nComp = stickMath_lib.pickFromProbDist(nCompDist);

            //Inner loop, will have a max number of attempts to generate a shape that fits the RF
            //If it fails within nAttempts, we will try again with a different nComp
            int nAttempts = 0;
            while (nAttempts < maxAttempts) {

                if (genMatchStick_comp(nComp)) {
                    int specialCompIndx = (int) (Math.random() * getnComponent() + 1);
                    this.setSpecialEndComp(Collections.singletonList(specialCompIndx));

                    centerShape();

                    boolean smoothSucceeded = smoothizeMStick();

                    if (!smoothSucceeded) // fail to smooth
                    {
                        continue; // else we need to gen another shape
                    }
                    try {
                        positionShape();
                    } catch (MorphException e) {
                        System.err.println("Morph EXCEPTION: " + e.getMessage());
                        continue;
                    }

                    break;
                }
                nAttempts++;
            }
            if (nAttempts == maxAttempts) {
                continue;
            }
            break;
        }
    }

    @Override
    public void genMatchStickFromShapeSpec(AllenMStickSpec inSpec, double[] rotation){
        genMatchStickFromShapeSpec(inSpec, rotation, inSpec.getmAxis().getSpecialEndComp());
    }

    public void genPartialFromFile(String fname, int compIdInRF) {
        String in_specStr;
        StringBuffer fileData = new StringBuffer(100000);
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

        in_specStr = fileData.toString();

        AllenMStickSpec inSpec = new AllenMStickSpec();
        inSpec = AllenMStickSpec.fromXml(in_specStr);

        genMatchStickFromShapeSpec(inSpec, new double[] {0,0,0}, Collections.singletonList(compIdInRF));
    }

    public void genMatchStickFromShapeSpec(AllenMStickSpec inSpec, double[] rotation, List<Integer> specialEndComp)
    {
        // i can't see how inSpec is changed by this function
        //but it seems to be the case........
        //AC: Alden, it's because you're not using deep copy of rotCenter and finalPos.
        cleanData();

        // 1. general info
        int nComp = inSpec.getmAxis().getnComponent();
        setnComponent(nComp);
        int i, j, k;

        // 1.5 AC Info
        setSpecialEnd(new LinkedList<>(inSpec.getmAxis().getSpecialEnd()));
        setSpecialEndComp(specialEndComp);
        setBaseComp(inSpec.getmAxis().getBaseComp());

        // 2. tube info
        for (i=1; i<=nComp; i++)
        {
            //debug
            //System.out.println("comp " + i + " : ");
            getComp()[i] = new AllenTubeComp();
            getComp()[i].setBranchUsed(inSpec.getmAxis().getTube()[i].isBranchUsed());
            getComp()[i].setConnectType(inSpec.getmAxis().getTube()[i].getConnectType());
            for (j=0; j<3; j++)
                for (k=0; k<2; k++)
                {
                    getComp()[i].getRadInfo()[j][k] = inSpec.getmAxis().getTube()[i].getRadInfo()[j][k];
                    // System.out.print(comp[i].radInfo[j][k] + " " );
                }
            //System.out.println(" " );

            getComp()[i].getmAxisInfo().setArcLen(inSpec.getmAxis().getTube()[i].getmAxis_arcLen());
            getComp()[i].getmAxisInfo().setRad(inSpec.getmAxis().getTube()[i].getmAxis_rad());
            getComp()[i].getmAxisInfo().setBranchPt(inSpec.getmAxis().getTube()[i].getmAxis_branchPt());
            //System.out.println("branchPt " + comp[i].mAxisInfo.branchPt);

            getComp()[i].getmAxisInfo().setTransRotHis_alignedPt(inSpec.getmAxis().getTube()[i].getTransRotHis_alignedPt());
            getComp()[i].getmAxisInfo().setTransRotHis_rotCenter(inSpec.getmAxis().getTube()[i].getTransRotHis_rotCenter());
            getComp()[i].getmAxisInfo().getTransRotHis_finalPos().set(new Point3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalPos()));
            //getComp()[i].getmAxisInfo().setTransRotHis_finalPos(new Point3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalPos()));
            getComp()[i].getmAxisInfo().getTransRotHis_finalTangent().set(new Vector3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalTangent()));
            //getComp()[i].getmAxisInfo().setTransRotHis_finalTangent(new Vector3d( inSpec.getmAxis().getTube()[i].getTransRotHis_finalTangent()));
            getComp()[i].getmAxisInfo().setTransRotHis_devAngle(inSpec.getmAxis().getTube()[i].getTransRotHis_devAngle());
        }

        // 3. endPt info
        setnEndPt(inSpec.getmAxis().getnEndPt());

        for (i=1; i<=getnEndPt(); i++)
        {
            getEndPt()[i] = new EndPt_struct();
            getEndPt()[i].setComp(inSpec.getmAxis().getEndPt()[i].getComp());
            getEndPt()[i].setuNdx(inSpec.getmAxis().getEndPt()[i].getuNdx());
            getEndPt()[i].setPos(new Point3d( inSpec.getmAxis().getEndPt()[i].getPos()));
            getEndPt()[i].setTangent(new Vector3d( inSpec.getmAxis().getEndPt()[i].getTangent()));
            getEndPt()[i].setRad(inSpec.getmAxis().getEndPt()[i].getRad());
        }

        // 4. juncPt info
        setnJuncPt(inSpec.getmAxis().getnJuncPt());
        for (i=1; i<=getnJuncPt(); i++)
        {
            getJuncPt()[i] = new JuncPt_struct();
            getJuncPt()[i].setnComp(inSpec.getmAxis().getJuncPt()[i].getnComp());
            getJuncPt()[i].setnTangent(inSpec.getmAxis().getJuncPt()[i].getnTangent());
            getJuncPt()[i].setRad(inSpec.getmAxis().getJuncPt()[i].getRad());
            getJuncPt()[i].setPos(new Point3d(inSpec.getmAxis().getJuncPt()[i].getPos()));

            for (j=1; j<= getJuncPt()[i].getnComp(); j++)
            {
                getJuncPt()[i].getCompIds()[j] = inSpec.getmAxis().getJuncPt()[i].getComp()[j];
                getJuncPt()[i].getuNdx()[j] = inSpec.getmAxis().getJuncPt()[i].getuNdx()[j];
            }
            for (j=1; j<= getJuncPt()[i].getnTangent(); j++)
            {
                getJuncPt()[i].getTangent()[j] = new Vector3d( inSpec.getmAxis().getJuncPt()[i].getTangent()[j]);
                getJuncPt()[i].getTangentOwner()[j] = inSpec.getmAxis().getJuncPt()[i].getTangentOwner()[j];
            }

        }

        // May 22nd, we find after GA
        // sometimes the tangent will be wrong direction
        // (while we assume the tangent in JuncPt, EndPt are correct
        // In this case we want to do the modifcation!
        // This might not be the ultimate solving way
        // but, just do it for now

        for (i=1; i<=nComp; i++) {
            getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
            getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
                    getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
                    getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
                    getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
                    getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
            getComp()[i].RadApplied_Factory(); // since we didn't save these info
        }



        // 5. final rotation info
        setFinalRotation(new double[3]);
        for (i=0; i<3; i++)
            getFinalRotation()[i] = inSpec.getmAxis().getFinalRotation()[i] + rotation[i];

        setFinalShiftinDepth(new Point3d());
        getFinalShiftinDepth().x = inSpec.getmAxis().getFinalShiftInDepth()[0];
        getFinalShiftinDepth().y = inSpec.getmAxis().getFinalShiftInDepth()[1];
        getFinalShiftinDepth().z = inSpec.getmAxis().getFinalShiftInDepth()[2];

        // 6. calculate the smooth vect and fac info

        // 2008, Nov, we should not do a rotation again here, since the original ShapeSpec info should already be rotated
        // again, or we should do it!
        //        this.finalRotateAllPoints( finalRotation[0], finalRotation[1], finalRotation[2]);

        boolean res;
        try {
            res = smoothizeMStick();
        } catch (NullPointerException e) {
            res = true;
            // TODO Auto-generated catch block
            e.printStackTrace();
        }
        if ( res == false) {
            System.out.println("Fail to smooth while using info from a shapeSpec");
            System.out.println("THIS SHOULD NOT HAPPEN");
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
            positionShape();
            return;
//			            if ( inSpec.getNVect() < 10) // this might happen, not sure
//			            {
//			//                System.out.println("no old smooth vertex info yet");
//			                return;
//			            }
//			            Point3d[] oriVecList = inSpec.getVectInfo();
//			            double vect_dist = 0.0;
//			            int nVect1 = this.obj1.nVect;
//			            int nVect2 = inSpec.getNVect();
//			            System.out.println("      vec # check " + nVect1 + " " + nVect2);
//			            if ( nVect1 != nVect2)
//			            {
//			                res = false;
//			                System.out.println("            vec # unmatch");
//			            }
//			            if ( res == true)
//			            {
//			                for (i= 1; i<= this.obj1.nVect; i++)
//			                {
//			                    Point3d p1 = new Point3d(obj1.vect_info[i]);
//			                    Point3d p2 = oriVecList[i];
//			                    vect_dist += p1.distance(p2);
//			                }
//			                System.out.println("            total vect dist is :" + vect_dist);
//			                if ( vect_dist > 5.0)
//			                    res = false;
//			            }
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
                getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().negate();

                for (i=1; i<=nComp; i++)
                {
                    getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
                    getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
                            getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
                            getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
                            getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
                            getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
                    getComp()[i].RadApplied_Factory(); // since we didn't save these info
                }

                res = smoothizeMStick();
                if ( res == false) // success to smooth
                {
                    System.out.println("Fail to smooth while using info from a shapeSpec");
                    System.out.println("THIS SHOULD NOT HAPPEN");
                }


                if ( res == true)
                {
                    Point3d[] oriVecList = inSpec.getVectInfo();
                    double vect_dist = 0.0;
                    int nVect1 = getObj1().getnVect();
                    int nVect2 = inSpec.getNVect();
                    System.out.println("vec # check " + nVect1 + " " + nVect2);
                    if ( nVect1 != nVect2)
                    {
                        res = false;
                        System.out.println("vec # unmatch");
                    }
                    if ( res == true)
                    {
                        for (i= 1; i<= getObj1().getnVect(); i++)
                        {
                            Point3d p1 = new Point3d(getObj1().vect_info[i]);
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
                    getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().negate();

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
                for (i=1; i<= getnEndPt(); i++)
                {
                    if (getEndPt()[i].getComp() == tryComp)
                    {
                        candidate[nCandidate].set( getEndPt()[i].getTangent());
                        candidate[nCandidate+1].set( getEndPt()[i].getTangent());
                        candidate[nCandidate+1].negate();
                        nCandidate +=2;
                    }
                }

                for (i=1; i<= getnJuncPt(); i++)
                {
                    for (j=1; j<= getJuncPt()[i].getnTangent(); j++)
                        if  (getJuncPt()[i].getTangentOwner()[j] == tryComp)
                        {
                            candidate[nCandidate].set( getJuncPt()[i].getTangent()[j]);
                            candidate[nCandidate+1].set( getJuncPt()[i].getTangent()[j]);
                            candidate[nCandidate+1].negate();
                            nCandidate +=2;

                        }
                }

                for (k=0; k< nCandidate; k++)
                {
                    //key line  ---> flip the tangent dir
                    System.out.println("try to assign comp " + tryComp + " with " + k + " candidate");
                    Vector3d oriVec = new Vector3d(getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent());
                    getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().set(candidate[k]);
                    //comp[tryComp].mAxisInfo.transRotHis_finalTangent.negate();
                    //if (tryComp > 1) //flip back last one
                    //comp[tryComp-1].mAxisInfo.transRotHis_finalTangent.negate();

                    for (i=1; i<=nComp; i++)
                    {
                        getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
                        getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
                                getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
                                getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
                                getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
                                getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
                        getComp()[i].RadApplied_Factory(); // since we didn't save these info
                    }

                    res = this.smoothizeMStick();
                    if ( res == false) // success to smooth
                    {
                        System.out.println("Fail to smooth while using info from a shapeSpec");
                        System.out.println("THIS SHOULD NOT HAPPEN");
                    }

                    if ( res == true)
                    {
                        Point3d[] oriVecList = inSpec.getVectInfo();
                        double vect_dist = 0.0;
                        int nVect1 = getObj1().getnVect();
                        int nVect2 = inSpec.getNVect();
                        System.out.println("vec # check " + nVect1 + " " + nVect2);
                        if ( nVect1 != nVect2)
                        {
                            res = false;
                            System.out.println("vec # unmatch");
                        }
                        if ( res == true)
                        {
                            for (i= 1; i<= getObj1().getnVect(); i++)
                            {
                                Point3d p1 = new Point3d(getObj1().vect_info[i]);
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
                        getComp()[tryComp].getmAxisInfo().getTransRotHis_finalTangent().set(oriVec);
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

            for (tryTimes = 1; tryTimes <= Math.pow(2, getnComponent()) -1; tryTimes++)
            {
                //key line  ---> flip the tangent dir
                System.out.println("try to flip times " + tryTimes);
                int[] flipState = new int[getnComponent()];
                int divider = (int) Math.pow(2, getnComponent()-1);
                int nowV = tryTimes;
                for (j=0; j <getnComponent(); j++)
                {
                    //System.out.println( j + " " + nowV + " " + divider);
                    flipState[j] = nowV / divider;
                    nowV = nowV % divider;
                    divider = divider /2;
                }

                //debug
                for (j=0; j<getnComponent(); j++)
                    System.out.print( flipState[j] + " " );
                System.out.println(" ");
                System.out.println("nComp " + nComp);
                System.out.println("nComponent " + getnComponent());
                for (j=1; j<=nComp; j++)
                    if (flipState[j-1] == 1)
                        getComp()[j].getmAxisInfo().getTransRotHis_finalTangent().negate();

                for (i=1; i<=nComp; i++)
                {
                    getComp()[i].getmAxisInfo().genArc( getComp()[i].getmAxisInfo().getRad(), getComp()[i].getmAxisInfo().getArcLen());
                    getComp()[i].getmAxisInfo().transRotMAxis(getComp()[i].getmAxisInfo().getTransRotHis_alignedPt(),
                            getComp()[i].getmAxisInfo().getTransRotHis_finalPos(),
                            getComp()[i].getmAxisInfo().getTransRotHis_rotCenter(),
                            getComp()[i].getmAxisInfo().getTransRotHis_finalTangent(),
                            getComp()[i].getmAxisInfo().getTransRotHis_devAngle());
                    getComp()[i].RadApplied_Factory(); // since we didn't save these info
                }

                res = this.smoothizeMStick();
                if ( res == false) // success to smooth
                {
                    System.out.println("Fail to smooth while using info from a shapeSpec");
                    System.out.println("THIS SHOULD NOT HAPPEN");
                }

                if ( res == true)
                {
                    Point3d[] oriVecList = inSpec.getVectInfo();
                    double vect_dist = 0.0;
                    int nVect1 = this.getObj1().getnVect();
                    int nVect2 = inSpec.getNVect();
                    System.out.println("vec # check " + nVect1 + " " + nVect2);
                    if ( nVect1 != nVect2)
                    {
                        res = false;
                        System.out.println("vec # unmatch");
                    }
                    if ( res == true)
                    {
                        for (i= 1; i<= getObj1().getnVect(); i++)
                        {
                            Point3d p1 = new Point3d(getObj1().vect_info[i]);
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
                        getComp()[j].getmAxisInfo().getTransRotHis_finalTangent().negate();

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

        positionShape();
    }


    @Override
    /**
     * No checking we aren't already doing in positionShape which ensures everything we need
     * relative to RF.
     */
    protected boolean checkMStick() {
        return true;
    }

    private boolean checkCompInRF(int compIndx, double thresholdPercentageInRF) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

        pointsToCheck.addAll(Arrays.asList(this.getComp()[compIndx].getVect_info()));
        int numPoints = 0;

        for (Point3d point: pointsToCheck){
            if (point != null) {
                numPoints++;
                if (rf.isInRF(point.x, point.y)) {
                    pointsInside.add(point);
                }
            }
        }

        double percentageInRF = (double) pointsInside.size() / numPoints;
        return percentageInRF >= thresholdPercentageInRF;
    }



    private boolean checkInAllInRF(double thresholdPercentageInRF) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

//        for (int i=1; i<=this.getnComponent(); i++){
//            pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
//        }
        pointsToCheck.addAll(Arrays.asList(this.getObj1().vect_info));
        pointsToCheck.removeIf(new Predicate<Point3d>() {
            @Override
            public boolean test(Point3d point) {
                return point == null;
            }
        });

        for (Point3d point: pointsToCheck){
//            System.out.println("Checking point: " + point.x + ", " + point.y);
            if (rf.isInRF(point.x, point.y)) {
                pointsInside.add(point);
            }
        }

        double percentageInRF = (double) pointsInside.size() / pointsToCheck.size();
        return percentageInRF >= thresholdPercentageInRF;
    }

    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
    }

    private void drawRF() {
        List<Coordinates2D> outline = rf.getOutline();

        // Assuming the Coordinates2D class has methods getX() and getY() to access coordinates.
        if (outline == null || outline.isEmpty()) {
            return; // Nothing to draw if the list is empty.
        }

        GL11.glDisable(GL11.GL_DEPTH_TEST);

        // Set the color to draw with, e.g., white
        GL11.glColor3f(1.0f, 1.0f, 1.0f); // RGB color values: White

        // Begin drawing lines
        GL11.glBegin(GL11.GL_LINE_LOOP); // GL_LINE_LOOP for a closed loop, GL_LINES for individual lines
        for (Coordinates2D coord : outline) {
            GL11.glVertex2f((float) coord.getX(), (float) coord.getY()); // Provide each vertex
        }
        GL11.glEnd(); // Finish drawing

        GL11.glEnable(GL11.GL_DEPTH_TEST);

    }


    @Override
    protected void positionShape() throws MorphException {

        Coordinates2D rfCenter;
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            int compInRF = getSpecialEndComp().get(0);
            System.out.println("specialEndComp: " + getSpecialEndComp());
            System.out.println("Comp in RF: " + compInRF);

            double percentageInsideRF = 1.0;
            double initialThresholdPercentageOutOfRF = 0.8;
            double reductionStep = 0.05; // Step to reduce thresholdPercentageOutOfRF
            double minThresholdPercentageOutOfRF = 0.1; // Minimum threshold percentage allowed

            int maxAttempts = 1000;

            while (initialThresholdPercentageOutOfRF >= minThresholdPercentageOutOfRF) {
                int nAttempts = 0;
                while (nAttempts < maxAttempts) {
                    // Choose random component to try to move inside of RF

                    // Choose a point inside of the chosen component to move
                    Point3d pointToMove = this.getComp()[compInRF].getMassCenter();

                    // Choose a random point inside the RF to move the chosen point to.
                    Coordinates2D point = RandomPointInConvexPolygon.generateRandomPoint(rf.getOutline());
                    Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                    movePointToDestination(pointToMove, destination);

                    if (checkCompInRF(compInRF, percentageInsideRF) &&
                            checkEnoughShapeOutOfRF(compInRF, initialThresholdPercentageOutOfRF)) {
                        return; // Exit if the condition is met
                    }
                    nAttempts++;
                }
                initialThresholdPercentageOutOfRF -= reductionStep; // Reduce threshold for next outer loop iteration
            }

            throw new MorphException("Could not find a point in the RF after " + maxAttempts + " attempts per threshold reduction");

        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();
            moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (!checkInAllInRF(1.0)) {
                throw new MorphException("Shape cannot fit in RF");
            }
        }
    }

    private boolean checkEnoughShapeOutOfRF(int compInRF, double thresholdPercentageOutOfRF){
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsOutside = new ArrayList<>();

        for (int i=1; i<=this.getnComponent(); i++){
            if (i != compInRF) {
                pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
            }
        }

        int numPoints = 0;

        for (Point3d point: pointsToCheck){
            if (point!= null) {
                numPoints++;
                if (!rf.isInRF(point.x, point.y)) {
                    pointsOutside.add(point);
                }
            }
        }

        double percentageOutOfRF = (double) pointsOutside.size() / numPoints;
        return percentageOutOfRF >= thresholdPercentageOutOfRF;

    }

    public RFStrategy getRfStrategy() {
        return rfStrategy;
    }
}