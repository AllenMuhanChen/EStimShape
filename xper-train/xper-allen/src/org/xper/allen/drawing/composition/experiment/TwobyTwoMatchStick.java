package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.MorphedMAxisArc;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.RadiusProfile;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point3d;
import java.util.Arrays;

public class TwobyTwoMatchStick extends ProceduralMatchStick {

    public void genFourthMatchStick(TwobyTwoMatchStick secondMatchStick, int drivingComponentIndex, TwobyTwoMatchStick thirdMatchStick){
        genComponentSwappedMatchStick(secondMatchStick, drivingComponentIndex, thirdMatchStick, drivingComponentIndex, 15);
    }

    public void genComponentSwappedMatchStick(AllenMatchStick matchStickToMorph, int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn, int maxAttempts) throws MorphException{

        int numAttempts = 0;
        while (numAttempts < maxAttempts || maxAttempts == -1) {
            try {
                copyFrom(matchStickToMorph);
                swapSkeleton(limbToSwapOut, matchStickContainingLimbToSwapIn, limbToSwapIn);
                swapRadius(limbToSwapOut, matchStickContainingLimbToSwapIn, limbToSwapIn);
                checkForTubeCollisions();
                centerShape();
                attemptSmoothizeMStick();
                positionShape();
                return;
            } catch (MorphException e) {
                System.out.println(e.getMessage());
                numAttempts++;
            }
        }

        throw new MorphException("Cannot generate matchstick after " + numAttempts + " attempts");


    }

    private void swapSkeleton(int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn) {
        //SWAP SKELETON
        try {
            //swap arc
            AllenTubeComp compToSwapIn = matchStickContainingLimbToSwapIn.getTubeComp(limbToSwapIn);

            try {
                newArc = new MorphedMAxisArc(compToSwapIn.getmAxisInfo());

                //Finding alignedPt from arc to swap in:
                    //We want to move the uNDX point of the arc associated with the juction point of the limb to swap in

                int alignedPt=-1;
                for (JuncPt_struct juncPt : matchStickContainingLimbToSwapIn.getJuncPt()) {
                    if (juncPt != null)
                        for (int i=1; i<=juncPt.getnComp(); i++){
                            if (juncPt.getCompIds()[i] == limbToSwapIn){
                                alignedPt = juncPt.getuNdx()[i];
                                break;
                            }

                        }
                }

                //Finding final pos from junction
                Point3d finalPos = null;
                for (JuncPt_struct juncPt : this.getJuncPt()) {
                    if (juncPt != null)
                        for (int i=1; i<=juncPt.getnComp(); i++){
                            if (juncPt.getCompIds()[i] == limbToSwapIn){
                                finalPos = new Point3d(juncPt.getPos());
                                break;
                            }
                        }
                }


                newArc.transRotMAxis(
                        alignedPt,
                        finalPos,
                        newArc.getTransRotHis_rotCenter(),
                        newArc.getTransRotHis_finalTangent(),
                        0);
//                checkJunctions(limbToSwapOut, newArc);

            } catch (Exception e) {
                e.printStackTrace();
                throw new MorphException("Cannot swap skeletons, causes collision");
            }
            //update
            updateJuncPtsForNewComp(limbToSwapOut);
            updateComponentInfo(limbToSwapOut);
            checkForCollisions(limbToSwapOut);
        } catch (MorphException e) {
            e.printStackTrace();
            throw new MorphException("Cannot swap skeletons, causes collision");
        }

        //UPDATE REST OF SKELETON
        updateEndPtsAndJunctionPositions();
    }

    private void swapRadius(int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn) {
        //SWAP RADIUS
        try {
            RadiusProfile newRadiusProfile = matchStickContainingLimbToSwapIn.retrieveOldRadiusProfile(limbToSwapIn);
            updateRadiusProfile(limbToSwapOut, newRadiusProfile);
            applyRadiusProfile();
        } catch (MorphException e){
            throw new MorphException("Cannot swap radius");
        }
    }

}