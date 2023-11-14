package org.xper.allen.drawing.composition.experiment;

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
    protected double[] PARAM_nCompDist = {0, 0.33, 0.67, 1.0, 0.0, 0.0, 0.0, 0.0};
    protected SphericalCoordinates objCenteredPositionTolerance = new SphericalCoordinates(5.0, Math.PI / 4, Math.PI / 4);
    public static final double NOISE_RADIUS_DEGREES = 8;
    public int maxAttempts = -1;

    /**
     * Generates a new matchStick from the base matchStick's driving component
     *
     * @param baseMatchStick
     * @param drivingComponentIndex
     */
    public void genMatchStickFromDrivingComponent(ExperimentMatchStick baseMatchStick, int drivingComponentIndex) {
        // calculate the object centered position of the base matchStick's drivingComponent
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp =
                calcObjCenteredPosForDrivingComp(baseMatchStick, drivingComponentIndex);

        int numAttempts = 0;
        this.maxAttempts = baseMatchStick.maxAttempts;
        while (numAttempts < this.maxAttempts || this.maxAttempts == -1) {
            while (numAttempts < this.maxAttempts || this.maxAttempts == -1) {
                if (genMatchStickFromLeaf(drivingComponentIndex, baseMatchStick)) {
                    positionShape();
                    break;
                }
                numAttempts++;
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
        if (numAttempts == this.maxAttempts) {
            throw new MorphException("Could not generate matchStick from driving component after " + this.maxAttempts + " attempts");
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
        Point3d noiseCenter = calculateNoiseOrigin(compIndx);
        List<Point2d> pointsOutside = new LinkedList<>();
        for (ConcaveHull.Point point: hullVertices){
            if (!isPointWithinCircle(new Point2d(point.getX(), point.getY()), new Point2d(noiseCenter.getX(), noiseCenter.getY()), NOISE_RADIUS_DEGREES)){
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

    public Point3d calculateNoiseOrigin(int specialCompIndx) {
        Point3d point3d = new Point3d();
        for (JuncPt_struct junc : getJuncPt()) {
            if (junc != null) {
                int numMatch = Arrays.stream(junc.getComp()).filter(x -> x == specialCompIndx).toArray().length;
                if (numMatch == 1) {
                    if (junc.getnComp() == 2) {
                        point3d = calcProjectionFromSingleCompJunction(specialCompIndx, junc);
                    } else if (junc.getnComp() > 2){
                        point3d = calcProjectionFromMultiCompJunction(specialCompIndx, junc);
                    }
                }
            }
        }

        return point3d;
    }

    private Point3d calcProjectionFromSingleCompJunction(Integer specialCompIndx, JuncPt_struct junc) {
        Point3d point3d;
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
        int baseCompIndx = junc.getComp()[junctionBaseCompIndex];

        // Find tangent to project along for noise origin
        int tangentOwnerIndx = baseCompIndx;
        Vector3d tangent = getJuncTangentForSingle(junc, tangentOwnerIndx);
        // Find point along base component to start the projection from
        int connectedCompIndx = junc.getComp()[junctionBaseCompIndex];
        Point3d[] connectedMpts = getComp()[connectedCompIndx].getmAxisInfo().getmPts();
        int junctionUNdx = junc.getuNdx()[junctionBaseCompIndex];
        Point3d startingPosition = choosePositionAlongMAxisFromJuncUNdx(junctionUNdx, connectedMpts);

        point3d = pointAlong2dTangent(startingPosition, tangent, NOISE_RADIUS_DEGREES);
        return point3d;
    }

    private Point3d calcProjectionFromMultiCompJunction(Integer specialCompIndx, JuncPt_struct junc) {
        Point3d point3d;
        // Collect tangents for this junction - excluding special component
        List<Vector3d> connectedTangents = new LinkedList<>();
        List<Integer> indxForTangent = new LinkedList<>();
        int[] connectedComps = junc.getComp();
        for (int connectedCompIndx : connectedComps){
            if (connectedCompIndx != 0 && connectedCompIndx != specialCompIndx) {
                Vector3d tangent = getJuncTangentForMulti(junc, connectedCompIndx);
                connectedTangents.add(tangent);
                indxForTangent.add(connectedCompIndx);
            }
        }

        // For every unique pair of tangents, find the external angle
        Map<List<Vector3d>, Double> externalAnglesForTangentPairs = new HashMap<>();
        Map<List<Vector3d>, List<Integer>> indicesForTangentPairs = new HashMap<>();
        for (int i = 0; i < connectedTangents.size(); i++){
            for (int j = i + 1; j < connectedTangents.size(); j++){
                Vector3d tangent1 = connectedTangents.get(i);
                Vector3d tangent2 = connectedTangents.get(j);
                double externalAngle = 2*Math.PI - tangent1.angle(tangent2);
                externalAnglesForTangentPairs.put(Arrays.asList(tangent1, tangent2), externalAngle);
                int index1 = indxForTangent.get(i);
                int index2 = indxForTangent.get(j);
                indicesForTangentPairs.put(Arrays.asList(tangent1, tangent2), Arrays.asList(index1, index2));
            }
        }
        System.out.println(externalAnglesForTangentPairs);

        // Get the pair with the smallest external angle
        List<Vector3d> tangentPairWithSmallestExternalAngle = Collections.min(externalAnglesForTangentPairs.entrySet(), Comparator.comparingDouble(Map.Entry::getValue)).getKey();
        List<Integer> compIndicesForSmallestExternalAngle = indicesForTangentPairs.get(tangentPairWithSmallestExternalAngle);

        // Calculate bisector of smallest external angle
        Vector2d bisector = new Vector2d();
        Vector2d tangent1 = new Vector2d(tangentPairWithSmallestExternalAngle.get(0).x, tangentPairWithSmallestExternalAngle.get(0).y);
        Vector2d tangent2 = new Vector2d(tangentPairWithSmallestExternalAngle.get(1).x, tangentPairWithSmallestExternalAngle.get(1).y);
        tangent1.normalize();
        tangent2.normalize();
        bisector.add(tangent1);
        bisector.add(tangent2);
        bisector.normalize();
        bisector.negate();
        Vector3d bisector_3d = new Vector3d(bisector.getX(), bisector.getX(), 0);

        // Calculate a starting point
        LinkedList<Point3d> startingPositions = new LinkedList<>();
        for (Integer compIndx: compIndicesForSmallestExternalAngle){
            Point3d startingPosition;
            int juncCompIndx = junc.getIndexOfComp(compIndx);
            int junctionUNdx = junc.getuNdx()[juncCompIndx];
            Point3d[] connectedMpts = getComp()[compIndx].getmAxisInfo().getmPts();
            startingPosition = choosePositionAlongMAxisFromJuncUNdx(junctionUNdx, connectedMpts);
            startingPositions.add(startingPosition);
        }
        // Calculate average of starting positions
        Point3d averageStartingPosition = new Point3d();
        for (Point3d startingPosition: startingPositions){
            averageStartingPosition.add(startingPosition);
        }
        averageStartingPosition.scale(1.0/startingPositions.size());

        point3d = pointAlong2dTangent(averageStartingPosition, bisector_3d, NOISE_RADIUS_DEGREES);
        return point3d;
    }

    private Point3d choosePositionAlongMAxisFromJuncUNdx(int junctionUNdx, Point3d[] connectedMpts) {
        Point3d startingPosition;
        if (junctionUNdx == 1) {
            startingPosition = connectedMpts[20];
        } else {
            startingPosition = connectedMpts[35];
        }
        return startingPosition;
    }

    private Vector3d getJuncTangentForMulti(JuncPt_struct junc, int tangentOwnerIndx) {
        Vector3d tangent = junc.getTangent()[tangentOwnerIndx];
        Vector3d reversedTangent = new Vector3d(tangent);
        reversedTangent.negate();
        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
        possibleTangents.add(tangent);
        possibleTangents.add(reversedTangent);
        tangent = getVectorPointingAtPoint(possibleTangents, junc.getPos(), getComp()[tangentOwnerIndx].getmAxisInfo().getmPts()[26]);
        return tangent;
    }

    private Vector3d getJuncTangentForSingle(JuncPt_struct junc, int tangentOwnerIndx) {
        Vector3d tangent = junc.getTangent()[tangentOwnerIndx];
        Vector3d reversedTangent = new Vector3d(tangent);
        reversedTangent.negate();
        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
        possibleTangents.add(tangent);
        possibleTangents.add(reversedTangent);
        tangent = getVectorPointingFurthestAwayFromPoint(possibleTangents, junc.getPos(), getComp()[tangentOwnerIndx].getmAxisInfo().getmPts()[26]);
        return tangent;
    }


    /**
     * Finds the vector from a list that points most directly at a given point from a specific starting point.
     *
     * @param vectors   The list of vectors.
     * @param startPoint The starting point from which the vectors originate.
     * @param target    The target point.
     * @return The vector that points most directly at the target point from the starting point.
     */
    private Vector3d getVectorPointingAtPoint(List<Vector3d> vectors, Point3d startPoint, Point3d target) {
        Vector3d directionToTarget = new Vector3d(target.x - startPoint.x, target.y - startPoint.y, target.z - startPoint.z);

        double maxDotProduct = -Double.MAX_VALUE;
        Vector3d mostDirectVector = null;

        for (Vector3d vec : vectors) {
            // Here, assume that vectors are already originating from the startPoint,
            // if not, you need to translate them by subtracting startPoint from their origin.
            Vector3d normalizedVec = new Vector3d(vec);
            normalizedVec.normalize();

            double dotProduct = normalizedVec.dot(directionToTarget);
            if (dotProduct > maxDotProduct) {
                maxDotProduct = dotProduct;
                mostDirectVector = vec;
            }
        }

        return mostDirectVector;
    }

    /**
     * Finds the vector from a list that points furthest away from a given point, considering a starting point for each vector.
     *
     * @param vectors     The list of vectors.
     * @param startPoint  The starting point from which each vector originates.
     * @param target      The target point.
     * @return The vector that points furthest away from the target point.
     */
    private Vector3d getVectorPointingFurthestAwayFromPoint(List<Vector3d> vectors, Point3d startPoint, Point3d target) {
        Vector3d directionToTarget = new Vector3d();
        directionToTarget.sub(target, new Vector3d(startPoint.x, startPoint.y, startPoint.z)); // Direction from start point to target

        double minDotProduct = Double.MAX_VALUE;
        Vector3d mostOppositeVector = null;

        for (Vector3d vec : vectors) {
            Vector3d normalizedVec = new Vector3d(vec);
            normalizedVec.normalize();

            Vector3d normalizedDirectionToTarget = new Vector3d(directionToTarget);
            normalizedDirectionToTarget.normalize();

            double dotProduct = normalizedVec.dot(normalizedDirectionToTarget);
            if (dotProduct < minDotProduct) {
                minDotProduct = dotProduct;
                mostOppositeVector = vec;
            }
        }

        return mostOppositeVector;
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

    public void setMaxAttempts(int maxAttempts) {
        this.maxAttempts = maxAttempts;
    }
}