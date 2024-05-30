package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.RandomPointInConvexPolygon;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;

public class RFUtils {
    public static double calculateMStickMaxSizeDiameterDegrees(RFStrategy rfStrategy, ReceptiveFieldSource rfSource) {
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            int maxLimbs = 4;
            return rfSource.getRFRadiusDegrees() * maxLimbs;
        } else {
            //TODO:
            return rfSource.getRFRadiusDegrees() * 2;
        }
    }

    public static void positionAroundRF(RFStrategy rfStrategy, AllenMatchStick mStick, ReceptiveField rf) throws MorphedMatchStick.MorphException {
        Coordinates2D rfCenter;
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            int compInRF = mStick.getSpecialEndComp().get(0);
            System.out.println("specialEndComp: " + mStick.getSpecialEndComp());
            System.out.println("Comp in RF: " + compInRF);

            double percentageInsideRF = 1.0;
            double initialThresholdPercentageOutOfRF = 0.8;
            double reductionStep = 0.05; // Step to reduce thresholdPercentageOutOfRF
            double minThresholdPercentageOutOfRF = 0.1; // Minimum threshold percentage allowed

            int numPointsToTry = 100;

            while (initialThresholdPercentageOutOfRF >= minThresholdPercentageOutOfRF) {
                // Generate a uniform span of points within the RF
                List<Coordinates2D> pointsToTest = generateUniformPointsInCircle(rf.getCenter(), rf.radius, numPointsToTry);
                // Permute the points
                Collections.shuffle(pointsToTest);

                for (Coordinates2D point : pointsToTest) {
                    Point3d pointToMove = mStick.getComp()[compInRF].getMassCenter();
                    Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                    mStick.movePointToDestination(pointToMove, destination);

                    if (checkCompInRF(compInRF, percentageInsideRF, mStick, rf) &&
                            checkEnoughShapeOutOfRF(compInRF, initialThresholdPercentageOutOfRF, rf, mStick)) {
                        System.out.println("Final position: " + mStick.getComp()[compInRF].getMassCenter());
                        return;
                    }
                }
                System.out.println("Reducing threshold percentage for points outside of RF");
                initialThresholdPercentageOutOfRF -= reductionStep; // Reduce threshold for next outer loop iteration
            }

            throw new MorphedMatchStick.MorphException("Could not find a point in the RF after testing " + numPointsToTry + " points per threshold reduction");

        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();
            mStick.moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (!checkAllInRF(1.0, rf, mStick)) {
                throw new MorphedMatchStick.MorphException("Shape cannot fit in RF");
            }
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
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

        pointsToCheck.addAll(Arrays.asList(mStick.getComp()[compIndx].getVect_info()));
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
        return percentageInRF >= thresholdPercentageInRF;
    }

    private static boolean checkAllInRF(double thresholdPercentageInRF, ReceptiveField rf, AllenMatchStick mStick) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

//        for (int i=1; i<=this.getnComponent(); i++){
//            pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
//        }
        pointsToCheck.addAll(Arrays.asList(mStick.getObj1().vect_info));

        for (Point3d point: pointsToCheck){
            if (point != null) {
                if (rf.isInRF(point.x, point.y)) {
                    pointsInside.add(point);
                }
            }
        }

        double percentageInRF = (double) pointsInside.size() / pointsToCheck.size();
        return percentageInRF >= thresholdPercentageInRF;
    }

    private static boolean checkEnoughShapeOutOfRF(int compInRF, double thresholdPercentageOutOfRF, ReceptiveField rf, AllenMatchStick matchStick){
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsOutside = new ArrayList<>();

        for (int i = 1; i<= matchStick.getnComponent(); i++){
            if (i != compInRF) {
                pointsToCheck.addAll(Arrays.asList(matchStick.getComp()[i].getVect_info()));
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