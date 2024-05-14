package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.AllenTubeComp;
import org.xper.allen.drawing.composition.noisy.ConcaveHull;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.MStickObj4Smooth;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import javax.vecmath.Vector3d;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedList;
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
    public Vector3d finalShiftVec;

    public EStimShapeProceduralMatchStick(RFStrategy rfStrategy, ReceptiveField rf) {
        this.rfStrategy = rfStrategy;
        this.rf = rf;
    }



    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
    }
//
//    @Override
//    protected void finalPositionShape() {
//        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
////            centerSpecialJunctionAtOrigin();
//            finalMoveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
//        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {
//            Coordinates2D rfCenter = rf.getCenter();
//            //We divide by the scale factor to counteract the scaling that happens in smoothing operation
//            //which will incorrectly rescale this translation, so we are dividing it here so it will cancel out.
//            finalMoveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));
//        } else {
//            throw new IllegalArgumentException("RFStrategy not recognized");
//        }
//
//    }
    @Override
    protected void centerShape(){
        moveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
    }

    @Override
    protected void positionShape() {
        if (rfStrategy.equals(RFStrategy.PARTIALLY_INSIDE)) {
//            centerSpecialJunctionAtOrigin();
            finalShiftVec = moveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
        } else if (rfStrategy.equals(RFStrategy.COMPLETELY_INSIDE)) {
            Coordinates2D rfCenter = rf.getCenter();
            //We divide by the scale factor to counteract the scaling that happens in smoothing operation
            //which will incorrectly rescale this translation, so we are dividing it here so it will cancel out.
//            moveCenterOfMassTo(new Point3d(rfCenter.getX() /  getScaleForMAxisShape(), rfCenter.getY() / getScaleForMAxisShape(), 0.0));
            finalShiftVec = moveCenterOfMassTo(new Point3d(rfCenter.getX(), rfCenter.getY(), 0.0));
        } else {
            throw new IllegalArgumentException("RFStrategy not recognized");
        }

    }
    @Override
    public void drawSkeleton(boolean showComponents) {
//		this.showComponents = true;
        int i;
        if (showComponents)
            for (i=1; i<=getnComponent(); i++) {
                float[][] colorCode= {
                        {1.0f, 1.0f, 1.0f},
                        {1.0f, 0.0f, 0.0f},
                        {0.0f, 1.0f, 0.0f},
                        {0.0f, 0.0f, 1.0f},
                        {0.0f, 1.0f, 1.0f},
                        {1.0f, 0.0f, 1.0f},
                        {1.0f, 1.0f, 0.0f},
                        {0.4f, 0.1f, 0.6f}
                };

                getComp()[i].drawSurfPt(colorCode[i-1],getScaleForMAxisShape(), finalShiftVec);

            }
        else
            getObj1().drawVect();
    }

    @Override
    public boolean smoothizeMStick()
    {
        showDebug = false;



        int i;
        MStickObj4Smooth[] MObj = new MStickObj4Smooth[getnComponent()+1];
        // 1. generate 1 tube Object for each TubeComp
        for (i=1; i<= getnComponent(); i++)
            MObj[i] = new MStickObj4Smooth(getComp()[i]); // use constructor to do the initialization

        if (getnComponent() == 1) {
            this.setObj1(MObj[1]);
            return true;
        }

        // 2. Start adding tube by tube
        MStickObj4Smooth nowObj = MObj[1]; // use soft copy is fine here
        for (i=2; i<= getnComponent(); i++) {
            int target = i;
            boolean res  = false;
            res = nowObj.objectMerge( MObj[target], false);
            if (res == false) {
//				System.err.println("FAIL AT OBJECT MERGE");
                return false;
            }
        }

        // 3. general smooth afterward
        nowObj.smoothVertexAndNormMat(6, 15); // smooth the vertex by 4 times. normal by 10times


        this.setObj1(MObj[1]);

        this.getObj1().rotateMesh(getFinalRotation());

        this.getObj1().scaleTheObj(getScaleForMAxisShape()); //AC: IMPORTANT CHANGE




        if (isDoCenterObject()) {
            setFinalShiftinDepth(this.getObj1().subCenterOfMass());
        }

        for (i=1; i<=getnComponent(); i++)
        {
            getComp()[i].setScaleOnce(false);
            Point3d[] vect_info = getComp()[i].getVect_info();
            for (Point3d point : vect_info) {
                if (point != null) {
                    point.scale(getScaleForMAxisShape());;
                }
            }
        }


        return true;
    }

    @Override
    protected Point3d chooseStartingPoint(JuncPt_struct junc, Vector3d tangent) {
        Vector3d reverseTangent = new Vector3d(tangent);
        reverseTangent.negate();

//        Point3d correctedJuncPos = new Point3d(junc.getPos());
//        Vector3d reverseShiftVec  = new Vector3d(finalShiftVec);
//        correctedJuncPos.add(reverseShiftVec);
//        correctedJuncPos.scale(getScaleForMAxisShape());
//        correctedJuncPos.add(finalShiftVec);

        Point3d startingPosition = choosePositionAlongTangent(
                reverseTangent,
                junc.getPos(), //this is shifted by applyTranslation
                junc.getRad() * getScaleForMAxisShape()); // this is not shifted by smoothize
        return startingPosition;
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