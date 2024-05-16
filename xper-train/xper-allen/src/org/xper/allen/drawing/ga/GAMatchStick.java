package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import java.util.*;
import java.util.function.Predicate;

/**
 * MatchSticks that are used to generate stimuli for the GA Experiment.
 * Includes:
 * 1. Morphing
 * 2. Checking if the shape is inside the Receptive Field partially or completely
 *
 */
public class GAMatchStick extends MorphedMatchStick {

    RFStrategy rfStrategy;
    ReceptiveField rf;
    double thresholdPercentageInRF;

    public GAMatchStick(ReceptiveField rf, RFStrategy rfStrategy) {
        this.rf = rf;
        this.rfStrategy = rfStrategy;
    }

    public GAMatchStick() {
    }

    @Override
    public void genMatchStickRand() {
        int nComp;
        int maxAttempts = 10;

        //Outer loop, wille change nComp until we find a shape that fits the RF
        while (true) {

            double[] nCompDist = getPARAM_nCompDist();
            nComp = stickMath_lib.pickFromProbDist(nCompDist);

            //Inner loop, will have a max number of attempts to generate a shape that fits the RF
            //If it fails within nAttempts, we will try again with a different nComp
            int nAttempts = 0;
            while (nAttempts < maxAttempts) {

                if (genMatchStick_comp(nComp)) {
                    int specialCompIndx = (int) (Math.random() * getnComponent() + 1);
                    this.setSpecialEndComp(Collections.singletonList(specialCompIndx));

                    centerShape();

                    boolean smoothSucceeded = smoothizeMStick();

                    if (!smoothSucceeded) // fail to smooth
                    {
                        continue; // else we need to gen another shape
                    }
                    try {
                        positionShape();
                    } catch (MorphException e) {
                        System.err.println("Morph EXCEPTION: " + e.getMessage());
                        continue;
                    }

                    break;
                }
                nAttempts++;
            }
            if (nAttempts == maxAttempts) {
                continue;
            }
            break;
        }
    }


    @Override
    /**
     * No checking we aren't already doing in positionShape which ensures everything we need
     * relative to RF.
     */
    protected boolean checkMStick() {
        return true;
    }

    private boolean checkCompInRF(int compIndx, double thresholdPercentageInRF) {
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsInside = new ArrayList<>();

        pointsToCheck.addAll(Arrays.asList(this.getComp()[compIndx].getVect_info()));
        pointsToCheck.removeIf(new Predicate<Point3d>() {
            @Override
            public boolean test(Point3d point) {
                return point == null;
            }
        });

        for (Point3d point: pointsToCheck){
            if (rf.isInRF(point.x, point.y)) {
                pointsInside.add(point);
            }
        }

        double percentageInRF = (double) pointsInside.size() / pointsToCheck.size();
        System.out.println("Percentage in RF: " + percentageInRF + " Threshold: " + thresholdPercentageInRF);
        return percentageInRF >= thresholdPercentageInRF;
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

    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
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
            int maxAttempts = 100;
            while (nAttempts < maxAttempts) {
                //Choose random component to try to move inside of RF
                int randomCompIndx = new Random().nextInt(this.getnComponent()) + 1;
                setSpecialEndComp(Collections.singletonList(randomCompIndx));

                //Choose a point inside of the chosen component to move
                Point3d pointToMove = this.getComp()[randomCompIndx].getMassCenter();

                //Choose a random point inside the RF to move the chosen point to.
                Coordinates2D point = RandomPointInConvexPolygon.generateRandomPoint(rf.getOutline());
                Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                movePointToDestination(pointToMove, destination);
                if (checkCompInRF(randomCompIndx, percentageInsideRF) &&
                        checkEnoughShapeOutOfRF(thresholdPercentageOutOfRF))
                    break;
                nAttempts++;
            }
            if (nAttempts == maxAttempts) {
                throw new MorphException("Could not find a point in the RF after 100 attempts");
            }

            //Step 5: Move the point to the destination
        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();

            moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (checkInAllInRF(1.0)) {
            } else {
                throw new MorphException("Shape cannot fit in RF");
            }
        }
    }

    private boolean checkEnoughShapeOutOfRF(double thresholdPercentageOutOfRF){
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsOutside = new ArrayList<>();

        for (int i=1; i<=this.getnComponent(); i++){
            pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
        }
        pointsToCheck.removeIf(new Predicate<Point3d>() {
            @Override
            public boolean test(Point3d point) {
                return point == null;
            }
        });

        for (Point3d point: pointsToCheck){
            if (!rf.isInRF(point.x, point.y)) {
                pointsOutside.add(point);
            }
        }

        double percentageOutOfRF = (double) pointsOutside.size() / pointsToCheck.size();
        System.out.println("Percentage out of RF: " + percentageOutOfRF + " Threshold: " + thresholdPercentageOutOfRF);
        return percentageOutOfRF >= thresholdPercentageOutOfRF;

    }




}