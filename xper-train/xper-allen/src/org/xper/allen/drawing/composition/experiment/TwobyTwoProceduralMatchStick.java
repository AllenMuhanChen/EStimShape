package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.RadiusProfile;

public class TwobyTwoProceduralMatchStick extends ProceduralMatchStick {

    public void genFourthMatchStick(TwobyTwoProceduralMatchStick secondMatchStick, int drivingComponentIndex, TwobyTwoProceduralMatchStick thirdMatchStick){
        genComponentSwappedMatchStick(secondMatchStick, drivingComponentIndex, thirdMatchStick, drivingComponentIndex);
    }

    public void genComponentSwappedMatchStick(AllenMatchStick matchStickToMorph, int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn) throws MorphException{
        copyFrom(matchStickToMorph);
        swapSkeleton(limbToSwapOut, matchStickContainingLimbToSwapIn, limbToSwapIn);
        swapRadius(limbToSwapOut, matchStickContainingLimbToSwapIn, limbToSwapIn);
        checkForTubeCollisions();

        MutateSUB_reAssignJunctionRadius();
        positionShape();
        attemptSmoothizeMStick();
    }

    private void swapSkeleton(int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn) {
        //SWAP SKELETON
        try {
            //swap arc
            AllenTubeComp compToSwapIn = matchStickContainingLimbToSwapIn.getTubeComp(limbToSwapIn);
            try {
                newArc = compToSwapIn.getmAxisInfo();
                checkJunctions(limbToSwapOut, newArc);

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
            applyRadiusProfile(limbToSwapOut);
        } catch (MorphException e){
            throw new MorphException("Cannot swap radius");
        }
    }

}