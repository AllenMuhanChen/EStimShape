package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenMAxisArc;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.NormalMorphDistributer;
import org.xper.allen.drawing.composition.noisy.ConcaveHull;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapCalculation;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector2d;
import javax.vecmath.Vector3d;
import java.util.*;
import java.util.function.BiConsumer;

public class ExperimentMatchStick extends MorphedMatchStick {
    protected final double[] PARAM_nCompDist = {0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    protected SphericalCoordinates objCenteredPositionTolerance = new SphericalCoordinates(5.0, Math.PI / 8, Math.PI / 8);
    public static final double NOISE_RADIUS_DEGREES = 8;
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
                checkInNoise(drivingComponentIndex);
                compareObjectCenteredPositionTo(objCenteredPosForDrivingComp);
                break;
            } catch (ObjectCenteredPositionException e) {
                System.out.println("Error with object centered position, retrying");
            } catch (NoiseException e) {
                System.out.println(e.getMessage());
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
                compareObjectCenteredPositionTo(originalObjCenteredPos);
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
                Map<Integer, SphericalCoordinates> objCentPosForBaseMatchSticksDrivingComp = calcObjCenteredPosForDrivingComp(this, drivingComponentIndex);
                compareObjectCenteredPositionTo(objCentPosForBaseMatchSticksDrivingComp);
                checkInNoise(drivingComponentIndex);
                break;
            } catch (ObjectCenteredPositionException e) {
                System.out.println("Object Centered Position is off. Retrying...");
            } catch (NoiseException e) {
                System.out.println(e.getMessage());
            } catch (MorphException e) {
                e.printStackTrace();
            }
        }
    }

    /**
     * Verify that specified components of new matchStick are all in a similar object centered position
     * as the base matchStick's components
     */
    public void compareObjectCenteredPositionTo(Map<Integer, SphericalCoordinates> toCompareToObjectCenteredPositionForComponents) {
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
    public static class ObjectCenteredPositionException extends RuntimeException{

        public ObjectCenteredPositionException(String message){
            super(message);
        }
    }

    public void checkInNoise(int compIndx){
        Point3d[] compVect_info = getComp()[compIndx].getVect_info();
        ArrayList<ConcaveHull.Point> concaveHullPoints = new ArrayList<>();
        for (Point3d point3d: compVect_info){
            if (point3d != null){
                concaveHullPoints.add(new ConcaveHull.Point(point3d.getX(), point3d.getY()));
            }
        }
        ConcaveHull concaveHull = new ConcaveHull();

        ArrayList<ConcaveHull.Point> hullVertices = concaveHull.calculateConcaveHull(concaveHullPoints, 10);
        Point3d noiseCenter = calculateNoiseOrigin();
        List<Point2d> pointsOutside = new LinkedList<>();
        for (ConcaveHull.Point point: hullVertices){
            if (!isPointWithinCircle(new Point2d(point.getX(), point.getY()), new Point2d(noiseCenter.getX(), noiseCenter.getY()), NOISE_RADIUS_DEGREES)){
//                System.out.println("Found point outside of noise circle");
                pointsOutside.add(new Point2d(point.getX(), point.getY()));
            }
        }
        System.out.println("Number of points outside of noise circle: " + pointsOutside.size() + " out of " + hullVertices.size());
        if (pointsOutside.size() > 0){
            throw new NoiseException("Found points outside of noise circle");
        }


    }

    private boolean isPointWithinCircle(Point2d point, Point2d center, double radius) {
        return point.distance(center) <= radius;
    }

    public Point3d calculateNoiseOrigin() {
        Point3d point3d = new Point3d();
        List<Integer> specialEnds = getSpecialEndComp();
        for (Integer specialCompIndx: specialEnds) {
            for (JuncPt_struct junc : getJuncPt()) {
                if (junc != null) {
                    int numMatch = Arrays.stream(junc.getComp()).filter(x -> x == specialCompIndx).toArray().length;
                    if (numMatch == 1) {

                        // Find some important info about the junction
                        int junctionSpecialCompIndex = -1;
                        int junctionBaseCompIndex = -1;
                        int[] connectedComps = junc.getComp();
                        for (int comp : connectedComps) {
                            if (comp == specialCompIndx && comp != 0) {
                                junctionSpecialCompIndex = comp;
                            }
                            else if (comp != specialCompIndx && comp != 0)
                                junctionBaseCompIndex = comp;
                            }

                        // Find tangent to project along for noise origin
                        Vector3d tangent = junc.getTangent()[junctionBaseCompIndex];
                        Vector3d reversedTangent = new Vector3d(tangent);
                        reversedTangent.negate();
                        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
                        possibleTangents.add(tangent);
                        possibleTangents.add(reversedTangent);
                        tangent = vectorPointingAtPoint(possibleTangents, getComp()[specialCompIndx].getmAxisInfo().getmPts()[26]);

                        // Find point along base component to start the projection from
                        int connectedCompIndx = junc.getComp()[junctionBaseCompIndex];
                        Point3d[] connectedMpts = getComp()[connectedCompIndx].getmAxisInfo().getmPts();
                        int junctionUNdx = junc.getuNdx()[junctionBaseCompIndex];
                        Point3d startingPosition;
                        if (junctionUNdx == 1) {
                            startingPosition = connectedMpts[26];
                        } else {
                            startingPosition = connectedMpts[26];
                        }

                        point3d = pointAlong2dTangent(startingPosition, tangent, NOISE_RADIUS_DEGREES);
                    }
                    //TODO: numMatch > 1
                }
            }
            System.out.println(point3d);
        }
        return point3d;
    }

    /**
     * Finds the vector from a list that points most directly at a given point.
     *
     * @param vectors The list of vectors.
     * @param target  The target point.
     * @return The vector that points most directly at the target point.
     */
    private Vector3d vectorPointingAtPoint(List<Vector3d> vectors, Point3d target) {
        Vector3d directionToTarget = new Vector3d(target.x, target.y, target.z);

        double maxDotProduct = -Double.MAX_VALUE;
        Vector3d mostDirectVector = null;

        for (Vector3d vec : vectors) {
            Vector3d normalizedVec = new Vector3d(vec);
            normalizedVec.normalize();

            Vector3d normalizedDirection = new Vector3d(directionToTarget);
            normalizedDirection.normalize();

            double dotProduct = normalizedVec.dot(normalizedDirection);
            if (dotProduct > maxDotProduct) {
                maxDotProduct = dotProduct;
                mostDirectVector = vec;
            }
        }

        return mostDirectVector;
    }

    /**
     * Computes a point along the 3D tangent from a given 3D point, with z set to 0.
     *
     * @param startPoint The starting 3D point.
     * @param tangent    The 3D tangent vector (not required to be normalized).
     * @param distance   The distance to move along the tangent.
     * @return A new 3D point along the tangent with z set to 0.
     */
    public static Point3d pointAlong2dTangent(Point3d startPoint, Vector3d tangent, double distance) {
        Vector2d projectedTangent = GaussianNoiseMapCalculation.projectTo2D(tangent);
        Point2d start2d = new Point2d(startPoint.x, startPoint.y);
        Point2d result2d = GaussianNoiseMapCalculation.point2dAlongTangent(start2d, projectedTangent, distance);
        return new Point3d(result2d.x, result2d.y, 0);
    }

    @Override
    public double[] getPARAM_nCompDist() {
        return PARAM_nCompDist;
    }
}