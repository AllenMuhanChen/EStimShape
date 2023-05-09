package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick.MorphException;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;

import javax.vecmath.Point3d;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.function.BiConsumer;

public class ExperimentMatchStick extends AllenMatchStick {
    protected final double[] PARAM_nCompDist = {0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 };
    protected SphericalCoordinates objCenteredPositionTolerance = new SphericalCoordinates(5.0, Math.PI/8, Math.PI/8);

    public void genFirstMatchStick(ExperimentMatchStick baseMatchStick, int drivingComponentIndex){
        // calculate the object centered position of the base matchStick's drivingComponent
        Point3d drivingComponentMassCenter = baseMatchStick.getMassCenterForComponent(drivingComponentIndex);
        SphericalCoordinates drivingComponentObjectCenteredPosition = CoordinateConverter.cartesianToSpherical(drivingComponentMassCenter);
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp = new HashMap<>();
        objCenteredPosForDrivingComp.put(drivingComponentIndex, drivingComponentObjectCenteredPosition);

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

    /**
     * Verify that specified components of new matchStick are all in a similar object centered position
     * as the base matchStick's components
     */
    public void checkObjectCenteredPosition(Map<Integer, SphericalCoordinates> targetObjectCenteredPositionForComponents){
        HashMap<Integer, SphericalCoordinates> actualObjectCenteredPositionForComponents = new HashMap<>();
        targetObjectCenteredPositionForComponents.forEach(new BiConsumer<Integer, SphericalCoordinates>() {
            @Override
            public void accept(Integer integer, SphericalCoordinates sphericalCoordinates) {
                Point3d massCenter = getMassCenterForComponent(integer);
                actualObjectCenteredPositionForComponents.put(integer, CoordinateConverter.cartesianToSpherical(massCenter));
            }
        });

        targetObjectCenteredPositionForComponents.forEach(new BiConsumer<Integer, SphericalCoordinates>() {
            @Override
            public void accept(Integer integer, SphericalCoordinates sphericalCoordinates) {
                SphericalCoordinates actualObjecctCenteredPosition = actualObjectCenteredPositionForComponents.get(integer);
                if (Math.abs(actualObjecctCenteredPosition.r - sphericalCoordinates.r) > objCenteredPositionTolerance.r ||
                        Math.abs(actualObjecctCenteredPosition.theta - sphericalCoordinates.theta) > objCenteredPositionTolerance.theta ||
                        Math.abs(actualObjecctCenteredPosition.phi - sphericalCoordinates.phi) > objCenteredPositionTolerance.phi){
                    throw new MorphException("Object Centered Position is off.");
                }
            }
        });
    }

    protected void positionShape() {
        centerCenterOfMassAtOrigin();
    }

    public void genSecondMatchStick(ExperimentMatchStick firstMatchStick) {

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

}