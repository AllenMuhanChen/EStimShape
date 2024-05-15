package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.JuncPt_struct;

import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
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
    RFStrategy rfStrategy;
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
    protected void positionShape() {
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
//            centerSpecialJunctionAtOrigin();
            moveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {
            Coordinates2D rfCenter = rf.getCenter();
            moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));
        } else {
            throw new IllegalArgumentException("RFStrategy not recognized");
        }

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