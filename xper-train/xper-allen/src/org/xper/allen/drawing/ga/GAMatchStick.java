package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import java.io.BufferedReader;
import java.io.FileReader;
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

    ReceptiveField rf;


    public GAMatchStick(ReceptiveField rf, RFStrategy rfStrategy, String textureType) {
        this.rf = rf;
        this.rfStrategy = rfStrategy;
        this.textureType = textureType;
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
    public void genMatchStickFromShapeSpec(AllenMStickSpec inSpec, double[] rotation){
        genMatchStickFromShapeSpec(inSpec, rotation, inSpec.getmAxis().getSpecialEndComp());
    }

    public void genPartialFromFile(String fname, int compIdInRF) {
        String in_specStr;
        StringBuffer fileData = new StringBuffer(100000);
        try
        {
            BufferedReader reader = new BufferedReader(
                    new FileReader(fname));
            char[] buf = new char[1024];
            int numRead=0;
            while((numRead=reader.read(buf)) != -1){
                String readData = String.valueOf(buf, 0, numRead);
                //System.out.println(readData);
                fileData.append(readData);
                buf = new char[1024];

            }
            reader.close();
        }
        catch (Exception e)
        {
            System.out.println("error in read XML spec file");
            System.out.println(e);
        }

        in_specStr = fileData.toString();

        AllenMStickSpec inSpec = new AllenMStickSpec();
        inSpec = AllenMStickSpec.fromXml(in_specStr);

        genMatchStickFromShapeSpec(inSpec, new double[] {0,0,0}, Collections.singletonList(compIdInRF));
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



    private boolean checkAllInRF(double thresholdPercentageInRF) {
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
    protected void positionShape() throws MorphException {

        Coordinates2D rfCenter;
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
            int compInRF = getSpecialEndComp().get(0);
            System.out.println("specialEndComp: " + getSpecialEndComp());
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
                    Point3d pointToMove = this.getComp()[compInRF].getMassCenter();

                    // Choose a random point inside the RF to move the chosen point to.
                    Coordinates2D point = RandomPointInConvexPolygon.generateRandomPoint(rf.getOutline());
                    Point3d destination = new Point3d(point.getX(), point.getY(), 0.0);
                    movePointToDestination(pointToMove, destination);

                    if (checkCompInRF(compInRF, percentageInsideRF) &&
                            checkEnoughShapeOutOfRF(compInRF, initialThresholdPercentageOutOfRF)) {
                        return; // Exit if the condition is met
                    }
                    nAttempts++;
                }
                initialThresholdPercentageOutOfRF -= reductionStep; // Reduce threshold for next outer loop iteration
            }

            throw new MorphException("Could not find a point in the RF after " + maxAttempts + " attempts per threshold reduction");

        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {

            rfCenter = rf.getCenter();
            moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));

            if (!checkAllInRF(1.0)) {
                throw new MorphException("Shape cannot fit in RF");
            }
        }
    }

    private boolean checkEnoughShapeOutOfRF(int compInRF, double thresholdPercentageOutOfRF){
        List<Point3d> pointsToCheck = new ArrayList<>();
        List<Point3d> pointsOutside = new ArrayList<>();

        for (int i=1; i<=this.getnComponent(); i++){
            if (i != compInRF) {
                pointsToCheck.addAll(Arrays.asList(this.getComp()[i].getVect_info()));
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

    public RFStrategy getRfStrategy() {
        return rfStrategy;
    }
}