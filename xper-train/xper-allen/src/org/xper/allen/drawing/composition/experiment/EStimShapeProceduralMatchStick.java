package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.ga.RandomPointInConvexPolygon;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.*;
import java.util.function.Predicate;

/**
 * MatchSticks that are used to generate stimuli for the EStimShape NAFC Experiment.
 *
 * Includes:
 * 1. the ability to generate mSticks from base components and generate delta trials.
 * 2. partially or completely inside Receptive Field behavior based on special limb.
 *
 */
public class EStimShapeProceduralMatchStick extends ProceduralMatchStick {
    public ReceptiveField rf;

    public EStimShapeProceduralMatchStick(RFStrategy rfStrategy, ReceptiveField rf) {
        this.rfStrategy = rfStrategy;
        this.rf = rf;
    }



    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
    }

    @Override
    protected void centerShape(){
        moveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
    }

    @Override
    /**
     * IF the strategy is to have the shape partially inside the RF, then center the shape at origin so it can partially enter the RF.
     * IF the strategy is to have shape entirely inside the RF, then we need center the shape at the RF center.
     *
     * This accomplishes the goal of keeping the image presented centered on fixation in either case.
     */
    protected void positionShape() throws MorphException {
        Coordinates2D rfCenter;
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {

            double percentageInsideRF = 1.0;
            double thresholdPercentageOutOfRF = 0.5;

            int nAttempts = 0;
            int maxAttempts = 1000;
            while (nAttempts < maxAttempts) {
                //Choose random component to try to move inside of RF
                int compIndx = this.getSpecialEndComp().get(0);

                //Choose a point inside of the chosen component to move
//                Point3d pointToMove = this.getComp()[compIndx].getMassCenter();
                Point3d pointToMove = this.getComp()[compIndx].getmAxisInfo().getTransRotHis_finalPos();

                //Choose a random point inside the RF to move the chosen point to.
                Coordinates2D point = RandomPointInConvexPolygon.generateRandomPoint(rf.getOutline());
                Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                movePointToDestination(pointToMove, destination);
                if (checkCompInRF(compIndx, percentageInsideRF) &&
                        checkEnoughShapeOutOfRF(thresholdPercentageOutOfRF))
                    break;
                nAttempts++;
            }
            if (nAttempts == maxAttempts) {
                throw new MorphException("Could not find a point in the RF after 100 attempts");
            }


        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();

            moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (checkInAllInRF(1.0)) {
            } else {
                throw new MorphException("Shape cannot fit in RF");
            }
        }
    }

    private boolean checkInAllInRF(double thresholdPercentageInRF) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

//        for (int i=1; i<=this.getnComponent(); i++){
//            pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
//        }
        pointsToCheck.addAll(Arrays.asList(this.getObj1().vect_info));
        pointsToCheck.removeIf(new Predicate<Point3d>() {
            @Override
            public boolean test(Point3d point) {
                return point == null;
            }
        });

        for (Point3d point: pointsToCheck){
//            System.out.println("Checking point: " + point.x + ", " + point.y);
            if (rf.isInRF(point.x, point.y)) {
                pointsInside.add(point);
            }
        }

        double percentageInRF = (double) pointsInside.size() / pointsToCheck.size();
        System.out.println("Percentage in RF: " + percentageInRF + " Threshold: " + thresholdPercentageInRF);
        return percentageInRF >= thresholdPercentageInRF;
    }

    private boolean checkEnoughShapeOutOfRF(double thresholdPercentageOutOfRF){
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsOutside = new ArrayList<>();

        pointsToCheck.addAll(Arrays.asList(this.getObj1().vect_info));
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
        System.out.println("Percentage out of RF: " + percentageOutOfRF + " Threshold: " + thresholdPercentageOutOfRF);
        return percentageOutOfRF >= thresholdPercentageOutOfRF;

    }





    private boolean checkCompInRF(int compIndx, double thresholdPercentageInRF) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

        pointsToCheck.addAll(Arrays.asList(this.getComp()[compIndx].getVect_info()));
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
        System.out.println("Percentage in RF: " + percentageInRF + " Threshold: " + thresholdPercentageInRF);
        return percentageInRF >= thresholdPercentageInRF;
    }

    @Override
    protected boolean checkMStick(int drivingComponentIndex) {
        try {
//            checkMStickSize(); //no need to check size with our old methods if we are testing if it's completely inside RF
//            checkInRF();
            return true;
        } catch (MorphException e) {
            System.out.println(e.getMessage());
        }
        return false;
    }


    private void checkInRF() throws MorphException {
        double fractionPointsInRFThreshold = 1;
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();


        if (rfStrategy == RFStrategy.COMPLETELY_INSIDE) {
            //ADD ALL POINTS OF THE MSTICK
            pointsToCheck.addAll(Arrays.asList(this.getObj1().vect_info));
            removeNullPoints(pointsToCheck);
        } else if (rfStrategy == RFStrategy.PARTIALLY_INSIDE) {
            for (int i=1; i<=this.getnComponent(); i++){
                if (i == this.getDrivingComponent()) {
                    pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
                }
            }
            removeNullPoints(pointsToCheck);
        } else{
            throw new IllegalArgumentException("RFStrategy not recognized");
        }

        for (Point3d point: pointsToCheck){
//            System.out.println("Checking point: " + point.x + ", " + point.y);
            if (rf.isInRF(point.x, point.y)) {
                pointsInside.add(point);
            }
        }

        double percentageInRF = (double) pointsInside.size() / pointsToCheck.size();
        System.out.println("Percentage in RF: " + percentageInRF + " Threshold: " + fractionPointsInRFThreshold);

        if (percentageInRF >= fractionPointsInRFThreshold) {
        }
        else
            throw new MorphException("Object not in RF");

    }

    private static void removeNullPoints(List<Point3d> pointsToCheck) {
        pointsToCheck.removeIf(new Predicate<Point3d>() {
            @Override
            public boolean test(Point3d point) {
                return point == null;
            }
        });
    }

    private void drawRF() {
        List<Coordinates2D> outline = rf.getOutline();

        // Assuming the Coordinates2D class has methods getX() and getY() to access coordinates.
        if (outline == null || outline.isEmpty()) {
            return; // Nothing to draw if the list is empty.
        }

        GL11.glDisable(GL11.GL_DEPTH_TEST);

        // Set the color to draw with, e.g., white
        GL11.glColor3f(1.0f, 1.0f, 1.0f); // RGB color values: White

        // Begin drawing lines
        GL11.glBegin(GL11.GL_LINE_LOOP); // GL_LINE_LOOP for a closed loop, GL_LINES for individual lines
        for (Coordinates2D coord : outline) {
            GL11.glVertex2f((float) coord.getX(), (float) coord.getY()); // Provide each vertex
        }
        GL11.glEnd(); // Finish drawing

        GL11.glEnable(GL11.GL_DEPTH_TEST);

    }
}