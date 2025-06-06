package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.util.*;

public class RFUtils {
    public static double calculateMStickMaxSizeDiameterDegrees(RFStrategy rfStrategy, double rfRadiusDegrees) {
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            int maxLimbs = 4;
            return rfRadiusDegrees * maxLimbs;
        } else {
            //TODO:
            return rfRadiusDegrees * 2;
        }
    }

    public static void positionAroundRF(RFStrategy rfStrategy, AllenMatchStick mStick, ReceptiveField rf, int numPointsToTry) throws MorphedMatchStick.MorphException {
        Coordinates2D rfCenter;
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            int compInRF = mStick.getSpecialEndComp().get(0);
            if (mStick.getComp()[compInRF] == null){
                throw new MorphedMatchStick.MorphException("Component " + compInRF + " is null");

            }
//            checkCompCanFitInRF(mStick, rf, compInRF);
            double percentageInsideRF = 1.0;

            double initialThresholdPercentageOutOfRF = 0.8;
            double reductionStep = 0.1; // Step to reduce thresholdPercentageOutOfRF
            double minThresholdPercentageOutOfRF = 0.0; // Minimum threshold percentage allowed

            double thresholdPercentageOutOfRF = initialThresholdPercentageOutOfRF;
            while (thresholdPercentageOutOfRF >= minThresholdPercentageOutOfRF) {
                // Generate a uniform span of points within the RF
                List<Coordinates2D> pointsToTest = generateUniformPointsInCircle(rf.getCenter(), rf.radius, numPointsToTry);
                // Permute the points
                Collections.shuffle(pointsToTest);

                for (Coordinates2D point : pointsToTest) {
                    Point3d pointToMove = mStick.getComp()[compInRF].getMassCenter();
                    Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                    mStick.movePointToDestination(pointToMove, destination);

                    if (checkCompInRF(compInRF, percentageInsideRF, mStick, rf) &&
                            checkEnoughShapeOutOfRF(compInRF, thresholdPercentageOutOfRF, rf, mStick)) {
                        return;
                    }
                }
                thresholdPercentageOutOfRF -= reductionStep; // Reduce threshold for next outer loop iteration
            }

            throw new MorphedMatchStick.MorphException("Could not find a point in the RF with at least" + thresholdPercentageOutOfRF + "% points outisde of RF after testing " + numPointsToTry + " points per threshold reduction");

        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();
            System.out.println("RF Center: " + rfCenter);
            mStick.moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (!checkAllInRF(1.0, rf, mStick)) {
                throw new MorphedMatchStick.MorphException("Shape cannot fit in RF");
            }
        }
    }

    public static void checkCompCanFitInRF(AllenMatchStick mStick, ReceptiveField rf, int compInRF) {
        Point3d[] box = AllenMatchStick.getBoundingBoxForVects(mStick.getComp()[compInRF].getnVect(), mStick.getComp()[compInRF].getVect_info());
        double boxWidth = box[1].x - box[0].x;
        double boxHeight = box[1].y - box[0].y;
        if (Math.max(boxWidth, boxHeight) > 2* rf.radius) {
            throw new MorphedMatchStick.MorphException("Component is too large to fit in RF");
        }
    }

    private static List<Coordinates2D> generateUniformPointsInCircle(Coordinates2D center, double radius, int numPoints) {
        List<Coordinates2D> points = new ArrayList<>();
        double angleStep = Math.PI * 2 / Math.sqrt(numPoints); // angle step to cover circle uniformly
        double radiusStep = radius / Math.sqrt(numPoints); // radial step to cover circle uniformly

        for (double r = radiusStep; r <= radius; r += radiusStep) {
            for (double angle = 0; angle < Math.PI * 2; angle += angleStep) {
                double x = center.getX() + r * Math.cos(angle);
                double y = center.getY() + r * Math.sin(angle);
                points.add(new Coordinates2D(x, y));
            }
        }

        return points;
    }

    private static boolean checkCompInRF(int compIndx, double thresholdPercentageInRF, AllenMatchStick mStick, ReceptiveField rf) {
        int numPointsInside = 0;
        List<Point3d> pointsToCheck = getCorrectedVectPoints(compIndx, mStick);

        int numPoints = 0;
        for (Point3d correctedPoint: pointsToCheck){
            if (correctedPoint != null) {
                numPoints++;
                if (rf.isInRF(correctedPoint.x, correctedPoint.y)) {
                    numPointsInside++;
                }
            }
        }



        double percentageInRF = (double) numPointsInside / numPoints;
        return percentageInRF >= thresholdPercentageInRF;
    }

    /**
     * matchstick comps' vect_info is not scaled by scale, however it is translated.
     *
     * We need to undo the translation by mass center to center it around the origin by its mass center, then do
     * the scaling, then translate it back to its original position.
     * @param compIndx
     * @param mStick
     * @return
     */
    public static List<Point3d> getCorrectedVectPoints(int compIndx, AllenMatchStick mStick) {
        Point3d massCenter = mStick.getMassCenter();
        List<Point3d> pointsToCheck = new ArrayList<>();
        for (Point3d point : mStick.getComp()[compIndx].getVect_info()){
            if (point != null)
                pointsToCheck.add(new Point3d(point));
        }

        for (Point3d pointToCorrect: pointsToCheck){
            if (pointToCorrect != null) {
                pointToCorrect.sub(massCenter);
                pointToCorrect.scale(mStick.getScaleForMAxisShape());
                pointToCorrect.add(massCenter);

            }
        }
        return pointsToCheck;
    }

    private static boolean checkAllInRF(double thresholdPercentageInRF, ReceptiveField rf, AllenMatchStick mStick) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

        for (int i = 1; i <= mStick.getnComponent(); i++) {
            pointsToCheck.addAll(getCorrectedVectPoints(i, mStick));
        }

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
        System.out.println("Percentage in RF: " + percentageInRF);
        return percentageInRF >= thresholdPercentageInRF;
    }

    /**
     * Check what percentage of the shape that does NOT include the component in the RF is outside of the RF
     * @param compInRF
     * @param thresholdPercentageOutOfRF
     * @param rf
     * @param matchStick
     * @return
     */
    private static boolean checkEnoughShapeOutOfRF(int compInRF, double thresholdPercentageOutOfRF, ReceptiveField rf, AllenMatchStick matchStick){
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsOutside = new ArrayList<>();

        for (int i = 1; i<= matchStick.getnComponent(); i++){
            if (i != compInRF) {
                pointsToCheck.addAll(getCorrectedVectPoints(i, matchStick));
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

    public static Coordinates2D polarToCartesian(double eccentricity, double angleDegrees) {
        double angle = angleDegrees * Math.PI / 180;
        double x = eccentricity * Math.cos(angle);
        double y = eccentricity * Math.sin(angle);
        return new Coordinates2D(x, y);
    }

    public static double cartesianToPolarAngle(Coordinates2D center) {
        double x = center.getX();
        double y = center.getY();
        return Math.atan2(y, x) * 180 / Math.PI;
    }
}