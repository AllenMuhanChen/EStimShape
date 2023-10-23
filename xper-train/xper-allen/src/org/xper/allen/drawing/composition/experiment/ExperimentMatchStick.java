package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.NormalMorphDistributer;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;

import javax.vecmath.Point3d;
import java.util.HashMap;
import java.util.Map;
import java.util.function.BiConsumer;

public class ExperimentMatchStick extends MorphedMatchStick {
    protected final double[] PARAM_nCompDist = {0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    protected SphericalCoordinates objCenteredPositionTolerance = new SphericalCoordinates(5.0, Math.PI / 8, Math.PI / 8);

    /**
     * Generates a new matchStick from the base matchStick's driving component
     *
     * @param baseMatchStick
     * @param drivingComponentIndex
     */
    public void genMatchStickFromDrivingComponent(TwobyTwoExperimentMatchStick baseMatchStick, int drivingComponentIndex) {
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
                compareObjectCenteredPositionWith(objCenteredPosForDrivingComp);
                break;
            } catch (ObjectCenteredPositionException e) {
                System.out.println("Error with object centered position, retrying");
            } catch (MorphException e) {
                e.printStackTrace();
            }
        }
    }

    protected Map<Integer, SphericalCoordinates> calcObjCenteredPosForDrivingComp(ExperimentMatchStick baseMatchStick, int drivingComponentIndex) {
        Point3d drivingComponentMassCenter = baseMatchStick.getMassCenterForComponent(drivingComponentIndex);
        SphericalCoordinates drivingComponentObjectCenteredPosition = CoordinateConverter.cartesianToSpherical(drivingComponentMassCenter);
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp = new HashMap<>();
        objCenteredPosForDrivingComp.put(drivingComponentIndex, drivingComponentObjectCenteredPosition);
        return objCenteredPosForDrivingComp;
    }

    /**
     * Generates a new matchStick from morphing the base component in the targetMatchStick
     *
     * @param targetMatchStick
     */
    public void genNewBaseMatchStick(ExperimentMatchStick targetMatchStick, int drivingComponentIndex) {
        int baseComponentIndex;
        if (drivingComponentIndex == 1) {
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
            genMorphedMatchStick(morphParametersForComponents, targetMatchStick);
            try {
                Map<Integer, SphericalCoordinates> originalObjCenteredPos = calcObjCenteredPosForDrivingComp(targetMatchStick, drivingComponentIndex);
                compareObjectCenteredPositionWith(originalObjCenteredPos);
                break;
            } catch (ObjectCenteredPositionException e) {
                System.out.println("Object Centered Position is off. Retrying...");
            } catch (MorphException e) {
                e.printStackTrace();
            }
        }
    }

    public void genNewDrivingComponentMatchStick(ExperimentMatchStick baseMatchStick, int drivingComponentIndex, double magnitude) {
        Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        morphParametersForComponents.put(drivingComponentIndex, new ComponentMorphParameters(magnitude, new NormalMorphDistributer(1.0)));

        while (true) {
            genMorphedMatchStick(morphParametersForComponents, baseMatchStick);
            try {
                compareObjectCenteredPositionWith(calcObjCenteredPosForDrivingComp(this, drivingComponentIndex));
                break;
            } catch (ObjectCenteredPositionException e) {
                System.out.println("Object Centered Position is off. Retrying...");
            } catch (MorphException e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Verify that specified components of new matchStick are all in a similar object centered position
     * as the base matchStick's components
     */
    public void compareObjectCenteredPositionWith(Map<Integer, SphericalCoordinates> toCompareToObjectCenteredPositionForComponents) {
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
                        Math.abs(actualObjectCenteredPosition.phi - sphericalCoordinates.phi) > objCenteredPositionTolerance.phi) {
                    throw new ObjectCenteredPositionException("Object Centered Position is off for component " + compIndex);
                }
            }
        });
    }

    protected void positionShape() {
        centerCenterOfMassAtOrigin();
    }

    public Point3d getMassCenterForComponent(int componentIndex) {
        Point3d cMass = new Point3d(0, 0, 0);
        AllenTubeComp targetComp = getComp()[componentIndex];
        int totalVect = targetComp.getnVect();
        for (int i = 1; i <= totalVect; i++) {
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

    public static class ObjectCenteredPositionException extends RuntimeException{
        public ObjectCenteredPositionException(String message){
            super(message);
        }
    }
}