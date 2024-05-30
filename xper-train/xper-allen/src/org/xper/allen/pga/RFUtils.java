package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.RandomPointInConvexPolygon;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Arrays;
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

            int maxAttempts = 500;

            while (initialThresholdPercentageOutOfRF >= minThresholdPercentageOutOfRF) {
                int nAttempts = 0;
                while (nAttempts < maxAttempts) {
                    // Choose random component to try to move inside of RF

                    // Choose a point inside of the chosen component to move
                    Point3d pointToMove = mStick.getComp()[compInRF].getMassCenter();

                    // Choose a random point inside the RF to move the chosen point to.
                    Coordinates2D point = RandomPointInConvexPolygon.generateRandomPoint(rf.getOutline());
                    Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                    mStick.movePointToDestination(pointToMove, destination);

                    if (checkCompInRF(compInRF, percentageInsideRF, mStick, rf) &&
                            checkEnoughShapeOutOfRF(compInRF, initialThresholdPercentageOutOfRF, rf, mStick)) {
                        System.out.println("Final position: " + mStick.getComp()[compInRF].getMassCenter());
                        return;
                    }
                    nAttempts++;
                }
                System.out.println("Reducing threshold percentage for points outside of RF");
                initialThresholdPercentageOutOfRF -= reductionStep; // Reduce threshold for next outer loop iteration
            }

            throw new MorphedMatchStick.MorphException("Could not find a point in the RF after " + maxAttempts + " attempts per threshold reduction");

        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();
            mStick.moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (!checkAllInRF(1.0, rf, mStick)) {
                throw new MorphedMatchStick.MorphException("Shape cannot fit in RF");
            }
        }
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

}