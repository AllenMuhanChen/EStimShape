package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.util.*;
import java.util.function.Predicate;

public class RFMatchStick extends MorphedMatchStick {
    public static Map<RFStrategy, Double> thresholdsForRFStrategy = new LinkedHashMap<>();
    static {
        thresholdsForRFStrategy.put(RFStrategy.PARTIALLY_INSIDE, 0.2);
        thresholdsForRFStrategy.put(RFStrategy.COMPLETELY_INSIDE, 1.0);
    }
    RFStrategy rfStrategy;
    ReceptiveField rf;
    double thresholdPercentageInRF;

    public RFMatchStick(ReceptiveField rf, RFStrategy rfStrategy) {
        this.rf = rf;
        this.rfStrategy = rfStrategy;
        this.thresholdPercentageInRF = thresholdsForRFStrategy.get(rfStrategy);
    }

    public RFMatchStick() {
    }

    @Override
    protected boolean checkMStick() {
        if (rf != null)
            return checkInRF(thresholdPercentageInRF);
        else{
            return true;
        }
    }

    private boolean checkInRF(double thresholdPercentageInRF) {
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
    protected void positionShape() {
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            moveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
        }
        else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {
            Coordinates2D rfCenter = rf.getCenter();
            System.out.println("Positioning to rfCenter: " + rfCenter.getX() + ", " + rfCenter.getY());
            moveCenterOfMassTo(new Point3d(rfCenter.getX()/getScaleForMAxisShape(), rfCenter.getY()/getScaleForMAxisShape(), 0.0));
        }
    }

}