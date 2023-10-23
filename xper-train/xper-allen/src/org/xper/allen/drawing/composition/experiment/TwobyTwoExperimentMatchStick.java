package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters.RadiusProfile;
import org.xper.allen.drawing.composition.morph.NormalMorphDistributer;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;

import javax.vecmath.Point3d;
import java.util.HashMap;
import java.util.Map;
import java.util.function.BiConsumer;

public class TwobyTwoExperimentMatchStick extends MorphedMatchStick {
    protected final double[] PARAM_nCompDist = {0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    protected SphericalCoordinates objCenteredPositionTolerance = new SphericalCoordinates(5.0, Math.PI/8, Math.PI/8);


    /**
     * Generates a new matchStick from the base matchStick's driving component
     * @param baseMatchStick
     * @param drivingComponentIndex
     */
    public void genFirstMatchStick(TwobyTwoExperimentMatchStick baseMatchStick, int drivingComponentIndex){
        // calculate the object centered position of the base matchStick's drivingComponent
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp =
                calcObjCenteredPosForDrivingComp(baseMatchStick, drivingComponentIndex);

        while (true) {
            while (true) {
                if (genMatchStickFromLeaf(drivingComponentIndex, baseMatchStick)) {
                    positionShape();
                    break;
                }
            }

            try {
                checkObjectCenteredPosition(objCenteredPosForDrivingComp);
                break;
            } catch (MorphException e) {
                e.printStackTrace();
            }
        }
    }

    private Map<Integer, SphericalCoordinates> calcObjCenteredPosForDrivingComp(TwobyTwoExperimentMatchStick baseMatchStick, int drivingComponentIndex) {
        Point3d drivingComponentMassCenter = baseMatchStick.getMassCenterForComponent(drivingComponentIndex);
        SphericalCoordinates drivingComponentObjectCenteredPosition = CoordinateConverter.cartesianToSpherical(drivingComponentMassCenter);
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp = new HashMap<>();
        objCenteredPosForDrivingComp.put(drivingComponentIndex, drivingComponentObjectCenteredPosition);
        return objCenteredPosForDrivingComp;
    }

    /**
     * Generates a new matchStick from morphing the base component in the firstMatchStick
     * @param firstMatchStick
     */
    public void genSecondMatchStick(TwobyTwoExperimentMatchStick firstMatchStick, int drivingComponentIndex){
        int baseComponentIndex;
        if (drivingComponentIndex == 1){
            baseComponentIndex = 2;
        } else if (drivingComponentIndex == 2) {
            baseComponentIndex = 1;
        } else {
            throw new IllegalArgumentException("drivingComponentIndex must be 1 or 2");
        }

        Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        morphParametersForComponents.put(baseComponentIndex, new ComponentMorphParameters(0.5, new NormalMorphDistributer(1.0)));
        while (true) {
            genMorphedMatchStick(morphParametersForComponents, firstMatchStick);
            try{
                checkObjectCenteredPosition(calcObjCenteredPosForDrivingComp(firstMatchStick, drivingComponentIndex));
                break;
            } catch (MorphException e){
                e.printStackTrace();
            }
        }
    }

    public void genThirdMatchStick(TwobyTwoExperimentMatchStick firstMatchStick, int drivingComponentIndex, double magnitude){
        Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        morphParametersForComponents.put(drivingComponentIndex, new ComponentMorphParameters(magnitude, new NormalMorphDistributer(1.0)));

        while (true) {
            genMorphedMatchStick(morphParametersForComponents, firstMatchStick);
            try{
//                checkObjectCenteredPosition(calcObjCenteredPosForDrivingComp(matchStickToMorph, drivingComponentIndex));
                break;
            } catch (MorphException e){
                e.printStackTrace();
            }
        }
    }

    public void genFourthMatchStick(TwobyTwoExperimentMatchStick secondMatchStick, int drivingComponentIndex, TwobyTwoExperimentMatchStick thirdMatchStick){
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



    /**
     * Verify that specified components of new matchStick are all in a similar object centered position
     * as the base matchStick's components
     */
    public void checkObjectCenteredPosition(Map<Integer, SphericalCoordinates> toCompareToObjectCenteredPositionForComponents){
        HashMap<Integer, SphericalCoordinates> actualObjectCenteredPositionForComponents = new HashMap<>();
        toCompareToObjectCenteredPositionForComponents.forEach(new BiConsumer<Integer, SphericalCoordinates>() {
            @Override
            public void accept(Integer integer, SphericalCoordinates sphericalCoordinates) {
                Point3d massCenter = getMassCenterForComponent(integer);
                actualObjectCenteredPositionForComponents.put(integer, CoordinateConverter.cartesianToSpherical(massCenter));
            }
        });

        toCompareToObjectCenteredPositionForComponents.forEach(new BiConsumer<Integer, SphericalCoordinates>() {
            @Override
            public void accept(Integer compIndex, SphericalCoordinates sphericalCoordinates) {
                SphericalCoordinates actualObjectCenteredPosition = actualObjectCenteredPositionForComponents.get(compIndex);
                if (Math.abs(actualObjectCenteredPosition.r - sphericalCoordinates.r) > objCenteredPositionTolerance.r ||
                        Math.abs(actualObjectCenteredPosition.theta - sphericalCoordinates.theta) > objCenteredPositionTolerance.theta ||
                        Math.abs(actualObjectCenteredPosition.phi - sphericalCoordinates.phi) > objCenteredPositionTolerance.phi){
                    throw new MorphException("Object Centered Position is off.");
                }
            }
        });
    }

    protected void positionShape() {
        centerCenterOfMassAtOrigin();
    }


    public Point3d getMassCenterForComponent(int componentIndex){
        Point3d cMass = new Point3d(0,0,0);
        AllenTubeComp targetComp = getComp()[componentIndex];
        int totalVect = targetComp.getnVect();
        for (int i = 1; i<= totalVect; i++){
            cMass.add(targetComp.getVect_info()[i]);
        }
        cMass.x /= totalVect;
        cMass.y /= totalVect;
        cMass.z /= totalVect;
        return cMass;
    }

    @Override
    public double[] getPARAM_nCompDist() {
        return PARAM_nCompDist;
    }
}