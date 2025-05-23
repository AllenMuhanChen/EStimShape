package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.*;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point3d;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TwoByTwoMatchStick extends ProceduralMatchStick {

    public TwoByTwoMatchStick(NAFCNoiseMapper noiseMapper) {
        super(noiseMapper);
    }

    public void doSmallMutation(EStimShapeTwoByTwoMatchStick mStickToMorph, List<Integer> compsToMorph, double magnitude, boolean doPositionShape, boolean doCheckNoise, boolean doCompareObjCenteredPos, List<Integer> compsToNoise){
        int nAttempts = 0;
        int maxAttempts = 10;
        SphericalCoordinates objCenteredPosTolerance = new SphericalCoordinates(magnitude, magnitude * 180 * Math.PI / 180, magnitude * 180 * Math.PI / 180);
        SphericalCoordinates originalObjCenteredPos = null;
        if (doCompareObjCenteredPos) {
            originalObjCenteredPos = calcObjCenteredPosForComp(this, getDrivingComponent());
        }

        while (nAttempts < maxAttempts) {
            nAttempts++;
            Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
            for (Integer compId: compsToMorph) {
                morphParametersForComponents.put(compId, new SetMorphParameters(magnitude));
            }
            try {
                genMorphedComponentsMatchStick(morphParametersForComponents, mStickToMorph, doPositionShape);
                if (doCheckNoise){
                    noiseMapper.checkInNoise(this, compsToNoise, 0.75);
                }
                if (doCompareObjCenteredPos) {
                    SphericalCoordinates newDrivingComponentPos = calcObjCenteredPosForComp(this, getDrivingComponent());
                    compareObjectCenteredPositions(originalObjCenteredPos, newDrivingComponentPos, objCenteredPosTolerance);
                }
                return;
            } catch (MorphedMatchStick.MorphException e) {
                copyFrom(mStickToMorph);
                System.out.println(e.getMessage());
                System.out.println("Retrying genSmallMutationMatchStick() " + nAttempts + " out of " + maxAttempts);
            }
        }
    }

    public void doMediumMutation(EStimShapeTwoByTwoMatchStick mStickToMorph, List<Integer> compsToMorph, Double magnitude, double discreteness, boolean doPositionShape, boolean doCheckNoise, List<Integer> compsToNoise){
        int nAttempts = 0;
        int maxAttempts = 10;
        copyFrom(mStickToMorph);
        System.out.println("Pre set mute driving comp: " + this.getDrivingComponent());
        System.out.println("Pre set mute center of mass: " + this.getMassCenterForComponent(getDrivingComponent()));
        System.out.println("Pre set mute real center: " + this.getComp()[this.getDrivingComponent()].getMassCenter());

        while (nAttempts < maxAttempts) {
            nAttempts++;
            Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
            for (Integer compId: compsToMorph) {
                morphParametersForComponents.put(compId, new NormalDistributedComponentMorphParameters(magnitude, new NormalMorphDistributer(discreteness),
                        90 * Math.PI / 180));
            }
            try {
                genMorphedComponentsMatchStick(morphParametersForComponents, mStickToMorph, doPositionShape);
                System.out.println("Post set mute driving comp: " + this.getDrivingComponent());
                System.out.println("Post set mute center of mass: " + this.getMassCenterForComponent(getDrivingComponent()));
                System.out.println("Post set mute real center: " + this.getComp()[this.getDrivingComponent()].getMassCenter());
                if (doCheckNoise){
                    noiseMapper.checkInNoise(this, compsToNoise, 0.4);
                }
                return;
            } catch (MorphedMatchStick.MorphException e) {
                copyFrom(mStickToMorph);
                System.out.println(e.getMessage());
                System.out.println("Retrying genMediumMutationMatchStick() " + nAttempts + " out of " + maxAttempts);
            }
        }
    }

    public void genSwappedBaseAndDrivingComponentMatchStick(TwoByTwoMatchStick secondMatchStick, int drivingComponentIndex, TwoByTwoMatchStick thirdMatchStick, boolean doPositionShape, int maxAttempts){

        genComponentSwappedMatchStick(secondMatchStick, drivingComponentIndex, thirdMatchStick, drivingComponentIndex, maxAttempts, doPositionShape);
    }


    public void genMatchStickFromComponentInNoise(ProceduralMatchStick baseMatchStick, int fromCompId, int nComp,
                                                  boolean doCompareObjCenteredPos, int maxAttempts, NAFCNoiseMapper noiseMapper) {
        SphericalCoordinates originalObjCenteredPos = null;
        if (doCompareObjCenteredPos) {
            originalObjCenteredPos = calcObjCenteredPosForComp(baseMatchStick, fromCompId);
        }
        if (nComp == 0){
            nComp = chooseNumComps();
        }
        int nAttempts = 0;
        while (nAttempts < maxAttempts || maxAttempts == -1) {
            nAttempts++;
            try {
                genMatchStickFromComponent(baseMatchStick, fromCompId, nComp, 5);
            } catch (MorphException e){
                System.out.println("Error with morph, retrying");
                System.out.println(e.getMessage());
                continue;
            }
            int drivingComponent = getDrivingComponent();
            List<Integer> compsToNoise = Collections.singletonList(drivingComponent);
            SphericalCoordinates newDrivingComponentPos = null;
            if (doCompareObjCenteredPos) {
                newDrivingComponentPos = calcObjCenteredPosForComp(this, drivingComponent);
                System.out.println("Original obj centered pos: " + originalObjCenteredPos.toString());
                System.out.println("New driving component pos: " + newDrivingComponentPos.toString());
            }
            try {
                noiseMapper.checkInNoise(this, compsToNoise, 0.5);
                if (doCompareObjCenteredPos)
                    compareObjectCenteredPositions(originalObjCenteredPos, newDrivingComponentPos, this.objCenteredPositionTolerance);
            } catch (Exception e) {
                System.out.println(e.getMessage());
                continue;
            }
            return;
        }
        throw new MorphRepetitionException("Could not generate matchStick FROM COMPONENT IN NOISE after " + maxAttempts + " attempts");
    }

    public void genComponentSwappedMatchStick(AllenMatchStick matchStickToMorph, int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn, int maxAttempts, boolean doPositionShape) throws MorphException{
        int numAttempts = 0;
        while (numAttempts < maxAttempts || maxAttempts == -1) {
            try {
                copyFrom(matchStickToMorph);
                swapSkeleton(limbToSwapOut, matchStickContainingLimbToSwapIn, limbToSwapIn);
                swapRadius(limbToSwapOut, matchStickContainingLimbToSwapIn, limbToSwapIn);
                checkForTubeCollisions();
                centerShape();
                attemptSmoothizeMStick();
                if (doPositionShape)
                    positionShape();
//                checkMStickSize();
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

            try {
                AllenTubeComp compToSwapIn = matchStickContainingLimbToSwapIn.getTubeComp(limbToSwapIn);

                newArc = new MorphedMAxisArc(compToSwapIn.getmAxisInfo());

                alignSwappedInLimbWithJunc(matchStickContainingLimbToSwapIn, limbToSwapIn, compToSwapIn);

            } catch (Exception e) {
                e.printStackTrace();
                throw new MorphException("Cannot swap skeletons, causes collision");
            }
            //update
            updateJuncPtsForNewComp(limbToSwapOut);
            updateComponentInfo(limbToSwapOut);
            checkForCollisions(limbToSwapOut);
        } catch (MorphException e) {
            System.out.println(e.getMessage());
            throw new MorphException("Cannot swap skeletons, causes collision");
        }

        //UPDATE REST OF SKELETON
        updateEndPtsAndJunctionPositions();
    }

    private void alignSwappedInLimbWithJunc(MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn, AllenTubeComp compToSwapIn) {
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
                0); //rotation already present in copied arc, don't want to rotate again
        //set rotation to match swapped in arc because transRotMAXis overrides
        newArc.setTransRotHis_devAngle(compToSwapIn.getmAxisInfo().getTransRotHis_devAngle());
    }

    private void swapRadius(int limbToSwapOut, MorphedMatchStick matchStickContainingLimbToSwapIn, int limbToSwapIn) {
        //SWAP RADIUS
        try {
            RadiusProfile newRadiusProfile = matchStickContainingLimbToSwapIn.retrieveOldRadiusProfile(limbToSwapIn);
            updateRadiusProfile(limbToSwapOut, newRadiusProfile);
            applyRadiusProfile();
        } catch (MorphException e){
            throw new MorphException("Cannot swap radius: " + e.getMessage());
        }
    }

    @Override
    public void genMorphedDrivingComponentMatchStick(ProceduralMatchStick baseMatchStick, double magnitude, double discreteness, boolean doPositionShape, boolean doCheckNoise, int maxAttempts) {
        int drivingComponentIndx = baseMatchStick.getSpecialEndComp().get(0);
        int numAttempts = 0;
        this.maxAttempts = maxAttempts;
        while (numAttempts < this.maxAttempts || this.maxAttempts == -1) {
            try {
                genNewComponentMatchStick(baseMatchStick, drivingComponentIndx, magnitude, discreteness, doPositionShape, 15);
//                centerShape();
            } catch(MorphException e) {
                System.out.println(e.getMessage());
                continue;
            } finally{
                numAttempts++;
            }

            try {
//                checkMStickSize();
                int newDrivingComponentIndx = getDrivingComponent();
                List<Integer> compsToNoise = Collections.singletonList(newDrivingComponentIndx);
                if (doCheckNoise)
                    noiseMapper.checkInNoise(this, compsToNoise, 0.7);
            } catch (MorphException e) {
                System.out.println(e.getMessage());
                continue;
            }

            break;
        }

    }

}