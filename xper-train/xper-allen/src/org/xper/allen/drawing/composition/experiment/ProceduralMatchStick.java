package org.xper.allen.drawing.composition.experiment;

import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.NormalDistributedComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.NormalMorphDistributer;
import org.xper.allen.drawing.composition.noisy.ConcaveHull;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapCalculation;
import org.xper.allen.util.CoordinateConverter;
import org.xper.allen.util.CoordinateConverter.SphericalCoordinates;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector2d;
import javax.vecmath.Vector3d;
import java.util.*;

/**
 * Matchsticks procedurally generated from base components, and delta versions of those matchsticks
 */
public class ProceduralMatchStick extends MorphedMatchStick {

    protected double[] PARAM_nCompDist = {0, 0.33, 0.67, 1.0, 0.0, 0.0, 0.0, 0.0};
    //protected double[] PARAM_nCompDist = {0, 0, 1, 0, 0.0, 0.0, 0.0, 0.0};
    protected SphericalCoordinates objCenteredPositionTolerance =
            new SphericalCoordinates(100, Math.PI / 4, Math.PI / 2 );
    public double noiseRadiusMm = 10;
    public int maxAttempts = 5;
    protected Point3d noiseOrigin;

    /**
     * Generates a new matchStick from the base matchStick's driving component
     *
     * @param baseMatchStick
     * @param morphComponentIndx
     * @param nComp if 0, then choose randomly
     * @param maxAttempts
     */
    public void genMatchStickFromComponent(ProceduralMatchStick baseMatchStick, int morphComponentIndx, int nComp, int maxAttempts) {
        // calculate the object centered position of the base matchStick's drivingComponent
//        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp =
//                calcObjCenteredPosForDrivingComp(baseMatchStick, drivingComponentIndex);
        if (nComp == 0){
            nComp = chooseNumComps();
        }
        int numAttempts = 0;
        while (numAttempts < maxAttempts || maxAttempts == -1) {
            System.out.println("ATtempting genMatchFromLeaf: " + numAttempts);
            if (genMatchStickFromLeaf(morphComponentIndx, baseMatchStick, nComp)) {
                return;
            } else{
                numAttempts++;
            }
        }
        throw new MorphRepetitionException("Could not generate matchStick FROM DRIVING COMPONENT after " + maxAttempts + " attempts");
    }



    public void genMorphedDrivingComponentMatchStick(ProceduralMatchStick baseMatchStick, double magnitude, double discreteness, boolean doPositionShape, boolean doCheckNoise) {
        int drivingComponentIndx = baseMatchStick.getSpecialEndComp().get(0);
        int numAttempts = 0;
        this.maxAttempts = baseMatchStick.maxAttempts;
        while (numAttempts < this.maxAttempts || this.maxAttempts == -1) {
            try {
                genNewComponentMatchStick(baseMatchStick, drivingComponentIndx, magnitude, discreteness, doPositionShape, 15);
            } catch(MorphException e) {
                System.out.println(e.getMessage());
                continue;
            } finally{
                numAttempts++;
            }

            checkMStickSize();
            break;
        }

    }

    public void genNewComponentMatchStick(ProceduralMatchStick baseMatchStick, int morphComponentIndx, double magnitude, double discreteness, boolean doPositionShape, int maxAttempts) {
        Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        morphParametersForComponents.put(morphComponentIndx, new NormalDistributedComponentMorphParameters(magnitude, new NormalMorphDistributer(discreteness)));

        int numAttempts = 0;
        while ((numAttempts < maxAttempts || maxAttempts == -1)) {
            try {
                genMorphedComponentsMatchStick(morphParametersForComponents, baseMatchStick, doPositionShape);
            } catch(MorphException e) {
                System.out.println(e.getMessage());
                continue;
            } finally{
                numAttempts++;
            }

            checkMStickSize();
            break;
        }
        if (numAttempts >= maxAttempts && maxAttempts != -1) {
            throw new MorphRepetitionException("Could not generate matchStick WITH NEW DRIVING COMP after " + maxAttempts + " attempts");
        }
    }

    protected void positionShape() {
    }

    public void genMatchStickFromComponentInNoise(ProceduralMatchStick baseMatchStick, int fromCompId, int nComp, boolean doCompareObjCenteredPos) {
        if (nComp == 0){
            nComp = chooseNumComps();
        }
        int nAttempts = 0;
        while (nAttempts < this.maxAttempts || this.maxAttempts == -1) {
            nAttempts++;
            try {
                genMatchStickFromComponent(baseMatchStick, fromCompId, nComp, this.maxAttempts);
            } catch (MorphException e){
                System.out.println("Error with morph, retrying");
                System.out.println(e.getMessage());
                continue;
            }
            int drivingComponent = getDrivingComponent();
            try {
                checkInNoise(drivingComponent, 0.3);
            } catch (Exception e) {
                System.out.println("Error with noise, retrying");
                System.out.println(e.getMessage());
                continue;
            }
            return;
        }
        throw new MorphRepetitionException("Could not generate matchStick FROM COMPONENT IN NOISE after " + this.maxAttempts + " attempts");
    }

    public int assignDeltaCompId() {
        int drivingComponent = getDrivingComponent();
        List<Integer> allComps = getCompIds();
        decideLeafBranch();
        boolean[] leafBranch = getLeafBranch();

        List<Integer> elegibleComps = new LinkedList<>();
        for (Integer compId : allComps) {
            if (compId != drivingComponent) {
                if (leafBranch[compId]) {
                    elegibleComps.add(compId);
                }
            }
        }

        //choose a random one
        int randIndex = (int) (Math.random() * elegibleComps.size());
        int deltaCompId = elegibleComps.get(randIndex);
        return deltaCompId;
    }

    public Integer getDrivingComponent() {
        return getSpecialEndComp().get(0);
    }

//    protected boolean validMStickSize() {
////        double buffer = 0.5; //in degrees, on each side. So total buffer is 1 degree
//        double maxRadius = getScaleForMAxisShape(); // degree
//        int i, j;
//
//        for (i = 1; i <= getnComponent(); i++) {
//            for (j = 1; j <= getComp()[i].getnVect(); j++) {
//                double xLocation = getComp()[i].getVect_info()[j].x;
//                double yLocation = getComp()[i].getVect_info()[j].y;
//
//                if(xLocation > maxRadius || xLocation < -maxRadius){
////					System.err.println("TOO BIG");
////					System.err.println("xLocation is: " + xLocation + ". maxBound is : " + maxRadius);
//                    return false;
//                }
//                if(yLocation > maxRadius || yLocation < -maxRadius){
////					System.err.println("TOO BIG");
////					System.err.println("yLocation is: " + yLocation + ". maxBound is : " + maxRadius);
//                    return false;
//                }
//            }
//        }
//        return true;
//    }

    public static class MorphRepetitionException extends MorphException{
        public MorphRepetitionException(String message){
            super(message);
        }
    }

    protected Map<Integer, SphericalCoordinates> calcObjCenteredPosMapForComp(ProceduralMatchStick baseMatchStick, int drivingComponentIndex) {
        Point3d shapeMassCenter = baseMatchStick.getMassCenter();
        Point3d drivingComponentMassCenter = baseMatchStick.getMassCenterForComponent(drivingComponentIndex);
        Point3d drivingComponentObjectCenteredPositionPoint = new Point3d(drivingComponentMassCenter);
        drivingComponentObjectCenteredPositionPoint.sub(shapeMassCenter);
        SphericalCoordinates drivingComponentObjectCenteredPosition = CoordinateConverter.cartesianToSpherical(drivingComponentObjectCenteredPositionPoint);
        Map<Integer, SphericalCoordinates> objCenteredPosForDrivingComp = new HashMap<>();
        objCenteredPosForDrivingComp.put(drivingComponentIndex, drivingComponentObjectCenteredPosition);
        return objCenteredPosForDrivingComp;
    }

    public static SphericalCoordinates calcObjCenteredPosForComp(ProceduralMatchStick matchStick, int compId) {
        Point3d shapeMassCenter = matchStick.getMassCenter();
        Point3d drivingComponentMassCenter = matchStick.getMassCenterForComponent(compId);
        Point3d drivingComponentObjectCenteredPositionPoint = new Point3d(drivingComponentMassCenter);
        drivingComponentObjectCenteredPositionPoint.sub(shapeMassCenter);
        return CoordinateConverter.cartesianToSpherical(drivingComponentObjectCenteredPositionPoint);
    }

    /**
     * Generates a new matchStick from morphing the base component in the targetMatchStick
     *
     * @param targetMatchStick
     * @param maxAttempts
     * @param doPositionShape
     * @param doCompareObjCenteredPos
     */
    public void genMorphedBaseMatchStick(ProceduralMatchStick targetMatchStick, int drivingComponentIndex, int maxAttempts, boolean doPositionShape, boolean doCompareObjCenteredPos) {
        int baseComponentIndex;
        List<Integer> baseCompIndcs = new LinkedList<>();
        for (int compId : targetMatchStick.getCompIds()) {
            if (compId != drivingComponentIndex) {
                baseCompIndcs.add(compId);
            }
        }


        //TODO: could refractor ComponentMorphParameters into data class and factory for different applications
        SphericalCoordinates originalObjCenteredPos = calcObjCenteredPosForComp(targetMatchStick, drivingComponentIndex);

        int nAttempts = 0;
        while (nAttempts < maxAttempts || maxAttempts == -1) {
            try {
                nAttempts++;
                Map<Integer, ComponentMorphParameters> morphParametersForComponents = new HashMap<>();
                NormalDistributedComponentMorphParameters morphParams = new NormalDistributedComponentMorphParameters(
                        0.7,
                        new NormalMorphDistributer(
                                1 / 3.0));
                for (int i = 0; i < baseCompIndcs.size(); i++) {
                    baseComponentIndex = baseCompIndcs.get(i);
                    morphParametersForComponents.put(baseComponentIndex, morphParams);
                }
                genMorphedComponentsMatchStick(morphParametersForComponents, targetMatchStick, doPositionShape);
                SphericalCoordinates newDrivingObjectCenteredPos = calcObjCenteredPosForComp(this, drivingComponentIndex);
                if (doCompareObjCenteredPos)
                    compareObjectCenteredPositions(originalObjCenteredPos, newDrivingObjectCenteredPos);
                checkMStickSize();
                checkLeafBaseRatio();
                return;
            } catch (ObjectCenteredPositionException e) {
                cleanData();
                this.setObj1(null);
                System.out.println("Error with object centered position, retrying");
                System.out.println(e.getMessage());
            } catch (MorphException e) {
                e.printStackTrace();
                cleanData();
                this.setObj1(null);
            }
        }

        if (nAttempts >= maxAttempts && maxAttempts != -1) {
            throw new MorphRepetitionException("Could not generate matchStick FROM BASE COMPONENT after " + this.maxAttempts + " attempts");
        }
    }

    private void checkLeafBaseRatio() {
        int leafIndx = getDrivingComponent();
        boolean succeed = vetLeafBaseSize(leafIndx);
        if (!succeed){
            throw new MorphException("Leaf to Base Size Ratio Check Failed");
        }
    }

    public void compareObjectCenteredPositions(SphericalCoordinates expected, SphericalCoordinates actual) {
        if (Math.abs(actual.r - expected.r) > objCenteredPositionTolerance.r ||
                angleDiff(actual.theta, expected.theta) > objCenteredPositionTolerance.theta ||
                angleDiff(actual.phi, expected.phi) > objCenteredPositionTolerance.phi) {
            throw new ObjectCenteredPositionException("Object Centered Position is off");
        }
    }

    public static void compareObjectCenteredPositions(SphericalCoordinates expected, SphericalCoordinates actual, SphericalCoordinates tolerances) {
        if (Math.abs(actual.r - expected.r) > tolerances.r ||
                angleDiff(actual.theta, expected.theta) > tolerances.theta ||
                angleDiff(actual.phi, expected.phi) > tolerances.phi) {
            throw new ObjectCenteredPositionException("Object Centered Position is off");
        }
    }

    protected Vector3d centerSpecialJunctionAtOrigin(){
        Point3d origin = new Point3d(0,0,0);
        Point3d specialJunctionPos = new Point3d(0,0,0);
        for (JuncPt_struct junc : getJuncPt()) {
            if (junc != null) {
                int numMatch = Arrays.stream(junc.getCompIds()).filter(x -> x == 1).toArray().length;
                if (numMatch == 1) {
                    specialJunctionPos = junc.getPos();
                }
            }
        }

        Vector3d shiftVec = new Vector3d();
        shiftVec.sub(origin, specialJunctionPos);
        applyTranslation(shiftVec);
        return shiftVec;
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
    public static class ObjectCenteredPositionException extends MorphException{

        public ObjectCenteredPositionException(String message){
            super(message);
        }
    }

    /**
     * checks if any part of the concave hull of specified comp is inside noise circle and
     * if enough of the rest of the shape is outside the noise circle
     * @param cantBeOutOfNoiseCompId
     * @param percentRequiredOutsideNoise
     */
    public void checkInNoise(int cantBeOutOfNoiseCompId, double percentRequiredOutsideNoise){
        AllenTubeComp testingComp = getComp()[cantBeOutOfNoiseCompId];
        Point3d[] compVect_info = testingComp.getVect_info();

        noiseOrigin = calculateNoiseOrigin(cantBeOutOfNoiseCompId);

        ArrayList<ConcaveHull.Point> pointsToCheck = new ArrayList<>();
        int index = 0;
        for (Point3d point3d: compVect_info){
            if (point3d != null){
                if (index % 1 == 0) //For speed, we only check every other point for the hull
                {
                    pointsToCheck.add(new ConcaveHull.Point(point3d.getX(), point3d.getY()));
                }
                index++;
            }
        }

        List<Point2d> pointsOutside = new LinkedList<>();
        for (ConcaveHull.Point point: pointsToCheck){
            if (!isPointWithinCircle(new Point2d(point.getX(), point.getY()), new Point2d(noiseOrigin.getX(), noiseOrigin.getY()), noiseRadiusMm)){
                pointsOutside.add(new Point2d(point.getX(), point.getY()));
            }
        }

        if (!pointsOutside.isEmpty()){
            throw new NoiseException("Found points outside of noise circle");
        }

        //Check if enough points not in compId are outside of the noise circle
        ArrayList<Point2d> pointsToCheckIfOutside = new ArrayList<>();
        for (int compIdx=1; compIdx<=getnComponent(); compIdx++){
            if (compIdx != cantBeOutOfNoiseCompId){
                Point3d[] compVectInfo = getComp()[compIdx].getVect_info();
                index = 0;
                for (Point3d point3d: compVectInfo){
                    if (point3d != null){
                        if (index % 1 == 0) //For speed, we only check every other point for the hull
                            pointsToCheckIfOutside.add(new Point2d(point3d.getX(), point3d.getY()));
                        index++;
                    }
                }
            }
        }

        int numPointsOutside = 0;
        for (Point2d point: pointsToCheckIfOutside){
            if (!isPointWithinCircle(point, new Point2d(noiseOrigin.getX(), noiseOrigin.getY()), noiseRadiusMm)){
                numPointsOutside++;
            }
        }
        double percentOutside = (double) numPointsOutside / pointsToCheckIfOutside.size();
        System.out.println("%%%% OUTSIDE: " + percentOutside);
        if (percentOutside < percentRequiredOutsideNoise){
            throw new NoiseException("Not enough points outside of noise circle");
        }
    }


    protected boolean isPointWithinCircle(Point2d point, Point2d center, double radius) {
        return point.distance(center) <= radius;
    }

    public Point3d calculateNoiseOrigin(int specialCompId) {
        Point3d point3d = new Point3d();
        for (JuncPt_struct junc : getJuncPt()) {
            if (junc != null) {
                int numMatch = Arrays.stream(junc.getCompIds()).filter(x -> x == specialCompId).toArray().length;
                if (numMatch == 1) {
                    if (junc.getnComp() == 2) {
                        point3d = calcProjectionFromSingleJunctionWithSingleComp(specialCompId, junc);
                    } else if (junc.getnComp() > 2){
                        point3d = calcProjectionFromJunctionWithMultiComp(specialCompId, junc);
                    }
                }
            }
        }

        return point3d;
    }

//
//    public Point3d getNoiseOriginToDraw(){
//        Point3d oldOrigin = this.noiseOrigin;
//
//    }

    protected Point3d calcProjectionFromSingleJunctionWithSingleComp(Integer specialCompIndx, JuncPt_struct junc) {
        Point3d projectedPoint;
        // Find some important info about the junction
        int baseCompId = -1;
        int[] connectedComps = junc.getCompIds();
        for (int comp : connectedComps) {
            if (comp != specialCompIndx && comp != 0) {
                baseCompId = comp;
            }
        }


        // Find tangent to project along for noise origin
        int tangentOwnerId = baseCompId;
        Vector3d tangent = getJuncTangentForSingle(junc, tangentOwnerId);
        tangent = new Vector3d(tangent.x, tangent.y, 0);
        // Find point along base component to start the projection from
//        Point3d[] connectedMpts = getComp()[baseCompId].getmAxisInfo().getmPts();
//        int junctionUNdx = junc.getuNdx()[junc.getJIndexOfComp(baseCompId)];
//        Point3d startingPosition = choosePositionAlongMAxisFromJuncUNdx(junctionUNdx, connectedMpts, 10);

        // Choose a starting point
        Point3d startingPosition = chooseStartingPoint(junc, tangent);
        System.out.println("Starting position: " + startingPosition);
        projectedPoint = pointAlong2dTangent(startingPosition,
                tangent,
                noiseRadiusMm);
        return projectedPoint;
    }

    protected Point3d chooseStartingPoint(JuncPt_struct junc, Vector3d tangent) {
        Vector3d reverseTangent = new Vector3d(tangent);
        reverseTangent.negate(); //reverse so we end up with a point inside of the shape
//        double shiftAmount = junc.getRad() * getScaleForMAxisShape();
//        double shiftAmount = 0;
        double shiftAmount = junc.getRad();
        Point3d startingPosition = choosePositionAlongTangent(
                reverseTangent,
                junc.getPos(), //this is shifted by applyTranslation
                shiftAmount); // this is not shifted by smoothize
        return startingPosition;
    }

    protected Point3d choosePositionAlongTangent(Vector3d tangent, Point3d pos, double distance) {
        Vector3d normalizedTangent = new Vector3d(tangent);
        normalizedTangent.normalize();
        normalizedTangent.scale(distance);
        Point3d startingPosition = new Point3d(pos);
        startingPosition.add(normalizedTangent);
        return startingPosition;

    }

    protected Point3d calcProjectionFromJunctionWithMultiComp(Integer specialCompId, JuncPt_struct junc) {
        Point3d projectedPoint;
        // Collect tangents for this junction - excluding special component
        List<Vector3d> nonSpecialTangents = new LinkedList<>();
        List<Integer> jIndicesForTangent = new LinkedList<>();
        int[] connectedCompIds = junc.getCompIds();
        for (int connectedCompId : connectedCompIds){
            if (connectedCompId != 0 && connectedCompId != specialCompId) {
                Vector3d tangent = getJuncTangentForMulti(junc, connectedCompId);
                nonSpecialTangents.add(tangent);
                jIndicesForTangent.add(junc.getJIndexOfComp(connectedCompId));
            }
        }

        // For every unique pair of tangents, find the external angle
        Map<List<Vector3d>, Double> externalAnglesForTangentPairs = new HashMap<>();
        Map<List<Vector3d>, List<Integer>> jIndicesForTangentPairs = new HashMap<>();
        for (int i = 0; i < nonSpecialTangents.size(); i++){
            for (int j = i + 1; j < nonSpecialTangents.size(); j++){
                Vector3d tangent1 = nonSpecialTangents.get(i);
                Vector3d tangent2 = nonSpecialTangents.get(j);
                double externalAngle = 2*Math.PI - tangent1.angle(tangent2);
                externalAnglesForTangentPairs.put(Arrays.asList(tangent1, tangent2), externalAngle);
                int jIndex1 = jIndicesForTangent.get(i);
                int jIndex2 = jIndicesForTangent.get(j);
                jIndicesForTangentPairs.put(Arrays.asList(tangent1, tangent2), Arrays.asList(jIndex1, jIndex2));
            }
        }

        // Get the pair with the smallest external angle
        List<Vector3d> tangentPairWithSmallestExternalAngle = Collections.min(externalAnglesForTangentPairs.entrySet(), Comparator.comparingDouble(Map.Entry::getValue)).getKey();
        List<Integer> jIndicesForSmallestExternalAngle = jIndicesForTangentPairs.get(tangentPairWithSmallestExternalAngle);

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
        Vector3d bisector_3d = new Vector3d(bisector.getX(), bisector.getY(), 0);

        // Calculate a starting point
//        LinkedList<Point3d> startingPositions = new LinkedList<>();
//        for (Integer jIndx: jIndicesForSmallestExternalAngle){

//            int junctionUNdx = junc.getuNdx()[jIndx];
//            Point3d[] connectedMpts = getComp()[junc.getCompIds()[jIndx]].getmAxisInfo().getmPts();
//            startingPosition = choosePositionAlongMAxisFromJuncUNdx(
//                    junctionUNdx, connectedMpts, 20);
//            startingPositions.add(startingPosition);
//        }

//         Calculate average of starting positions
//        Point3d averageStartingPosition = new Point3d();
//        for (Point3d startingPosition: startingPositions){
//            averageStartingPosition.add(startingPosition);
//        }
//        averageStartingPosition.scale(1.0/startingPositions.size());
        Point3d startingPosition = chooseStartingPoint(junc, bisector_3d);
        projectedPoint = pointAlong2dTangent(startingPosition, bisector_3d, noiseRadiusMm);
        return projectedPoint;
    }

    private Point3d choosePositionAlongMAxisFromJuncUNdx(int junctionUNdx, Point3d[] connectedMpts, int distanceFromJunction) {
        Point3d startingPosition;
        if (junctionUNdx == 1) {
            startingPosition = connectedMpts[1+ distanceFromJunction];
        } else {
            startingPosition = connectedMpts[51- distanceFromJunction];
        }
        return startingPosition;
    }

    private Vector3d getJuncTangentForMulti(JuncPt_struct junc, int tangentOwnerCompId) {
//        Vector3d tangent = junc.getTangent()[junc.getTangentOwner()[tangentOwnerId]];
        Vector3d tangent = junc.getTangentOfOwner(tangentOwnerCompId);
        Vector3d reversedTangent = new Vector3d(tangent);
        reversedTangent.negate();
        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
        possibleTangents.add(tangent);
        possibleTangents.add(reversedTangent);
        tangent = getVectorPointingAtPoint(possibleTangents, junc.getPos(), getComp()[tangentOwnerCompId].getmAxisInfo().getmPts()[26]);
        return tangent;
    }

    private Vector3d getJuncTangentForSingle(JuncPt_struct junc, int tangentOwnerId) {
        Vector3d tangent = junc.getTangentOfOwner(tangentOwnerId);
        Vector3d reversedTangent = new Vector3d(tangent);
        reversedTangent.negate();
        ArrayList<Vector3d> possibleTangents = new ArrayList<>(2);
        possibleTangents.add(tangent);
        possibleTangents.add(reversedTangent);
        tangent = getVectorPointingFurthestAwayFromPoint(possibleTangents, junc.getPos(), getComp()[tangentOwnerId].getmAxisInfo().getmPts()[26]);
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

    public void genMatchStickRand() {
        int nComp = chooseNumComps();
        genMatchStickRand(nComp);
    }

    public static int chooseNumComps() {
        int nComp;
        ProceduralMatchStick tempStick = new ProceduralMatchStick();
        double[] nCompDist = tempStick.getPARAM_nCompDist();
        nComp = stickMath_lib.pickFromProbDist(nCompDist);
        return nComp;
    }

    public void genMatchStickRand(int nComp) {
        while (true) {
            while (true) {
                if (genMatchStick_comp(nComp)) {
                    break;
                }
            }

            centerShape();
            boolean res = smoothizeMStick();
            res = res && validMStickSize();
            if (res) {
                break;
            }// else we need to gen another shape
        }
    }

    @Override
    public double[] getPARAM_nCompDist() {
        return PARAM_nCompDist;
    }

    public void setMaxAttempts(int maxAttempts) {
        this.maxAttempts = maxAttempts;
    }

    public Point3d getNoiseOrigin() {
        return noiseOrigin;
    }
}