package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.morph.*;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.MStickObj4Smooth;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import java.util.List;

public class EStimShapeTwoByTwoMatchStick extends TwoByTwoMatchStick {

    private final RFStrategy rfStrategy;
    private final ReceptiveField rf;


    public EStimShapeTwoByTwoMatchStick(RFStrategy rfStrategy, ReceptiveField rf, NoiseMapper noiseMapper) {
        super(noiseMapper);
        this.rfStrategy = rfStrategy;
        this.rf = rf;
        this.noiseRadiusMm = rf.radius*3;
    }



    @Override
    public void genMatchStickRand(int nComp) {
        while (true) {
            while (true) {
                if (genMatchStick_comp(nComp)) {
                    break;
                }
            }

            centerShape();
            boolean res = smoothizeMStick();
            if (res) {
                break;
            }// else we need to gen another shape
        }
    }

    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
        //NOISE
        double radius = noiseRadiusMm;

        Point3d noiseOrigin = this.getNoiseOrigin();
        Coordinates2D center = new Coordinates2D(noiseOrigin.getX(), noiseOrigin.getY());
        //draw noise
        if (radius <= 0 || center == null) {
            return;
        }

        GL11.glDisable(GL11.GL_DEPTH_TEST);

        // Set the color to draw with, e.g., white

        // Begin drawing the circle
        GL11.glBegin(GL11.GL_LINE_LOOP); // GL_LINE_LOOP for a closed loop
        GL11.glColor3f(1.0f, 0.0f, 0.0f);

        int numSegments = 100; // Number of segments to approximate the circle
        double angleIncrement = 2.0 * Math.PI / numSegments;

        for (int i = 0; i < numSegments; i++) {
            double angle = i * angleIncrement;
            float x = (float) (center.getX() + radius * Math.cos(angle));
            float y = (float) (center.getY() + radius * Math.sin(angle));
            GL11.glVertex2f(x, y); // Provide each vertex
        }

        GL11.glEnd(); // Finish drawing

        GL11.glEnable(GL11.GL_DEPTH_TEST);
//        draw_debug_gaussian_mapper();

    }

    /**
     * deprecrated
     */
    private void draw_debug_gaussian_mapper() {
        if(noiseMapper!=null){
            //ALL POINTS FROM THE OBJ1
            GL11.glColor4f(1.0f, 1.0f, 0.0f, 0.5f);
            List<Point2d> pointsToDraw = ((GaussianNoiseMapper) noiseMapper).debug_points_obj1;
            for (Point2d point : pointsToDraw) {
                GL11.glPointSize(0.1f);
                GL11.glBegin(GL11.GL_POINTS);
                GL11.glVertex2d(point.x, point.y);
                GL11.glEnd();
            }

            //ALL POINTS FROM VECT_INFO of in Noise comp
            GL11.glColor4f(0.0f, 0.0f, 1.0f, 0.5f);
            List<Point2d> pointsToDraw_all = ((GaussianNoiseMapper) noiseMapper).debug_points_vect;
            for (Point2d point : pointsToDraw_all) {
                GL11.glPointSize(0.1f);
                GL11.glBegin(GL11.GL_POINTS);
                GL11.glVertex2d(point.x, point.y);
                GL11.glEnd();
            }

            //OUTSIDE OF NOISE POINTS
            GL11.glDisable(GL11.GL_DEPTH_TEST);
            GL11.glColor4f(0.0f, 1.0f, 0.0f, 0.5f);
            List<Point2d> pointsToDraw_outside = ((GaussianNoiseMapper) noiseMapper).debug_points_outside;
            for (Point2d point : pointsToDraw_outside) {
                GL11.glPointSize(0.1f);
                GL11.glBegin(GL11.GL_POINTS);
                GL11.glVertex2d(point.x, point.y);
                GL11.glEnd();
            }
        }

        //NOISE
        double radius = noiseRadiusMm;
        ;
        Point2d debugNoiseOrigin = ((GaussianNoiseMapper) noiseMapper).debug_noise_origin;
        Coordinates2D center = new Coordinates2D(debugNoiseOrigin.getX(), debugNoiseOrigin.getY());
        //draw noise
        if (radius <= 0 || center == null) {
            return;
        }

        GL11.glDisable(GL11.GL_DEPTH_TEST);

        // Set the color to draw with, e.g., white

        // Begin drawing the circle
        GL11.glBegin(GL11.GL_LINE_LOOP); // GL_LINE_LOOP for a closed loop
        GL11.glColor3f(1.0f, 0.0f, 0.0f);

        int numSegments = 100; // Number of segments to approximate the circle
        double angleIncrement = 2.0 * Math.PI / numSegments;

        for (int i = 0; i < numSegments; i++) {
            double angle = i * angleIncrement;
            float x = (float) (center.getX() + radius * Math.cos(angle));
            float y = (float) (center.getY() + radius * Math.sin(angle));
            GL11.glVertex2f(x, y); // Provide each vertex
        }

        GL11.glEnd(); // Finish drawing

        GL11.glEnable(GL11.GL_DEPTH_TEST);
    }

    @Override
    public void centerShape(){
        moveCenterOfMassTo(new Point3d(0.0, 0.0, 0.0));
    }


    @Override
    public void positionShape() throws MorphedMatchStick.MorphException {
        RFUtils.positionAroundRF(rfStrategy, this, rf);
    }


    private void drawRF() {
        double radius = rf.getRadius();
        Coordinates2D center = rf.getCenter();

        if (radius <= 0 || center == null) {
            return; // Nothing to draw if radius is zero or negative, or center is null.
        }

        GL11.glDisable(GL11.GL_DEPTH_TEST);

        // Set the color to draw with, e.g., white
        GL11.glColor3f(1.0f, 1.0f, 1.0f); // RGB color values: White

        // Begin drawing the circle
        GL11.glBegin(GL11.GL_LINE_LOOP); // GL_LINE_LOOP for a closed loop

        int numSegments = 100; // Number of segments to approximate the circle
        double angleIncrement = 2.0 * Math.PI / numSegments;

        for (int i = 0; i < numSegments; i++) {
            double angle = i * angleIncrement;
            float x = (float) (center.getX() + radius * Math.cos(angle));
            float y = (float) (center.getY() + radius * Math.sin(angle));
            GL11.glVertex2f(x, y); // Provide each vertex
        }

        GL11.glEnd(); // Finish drawing

        GL11.glEnable(GL11.GL_DEPTH_TEST);
    }

    @Override
    /**
     * isScale parameter was added to this. This is because brand new match sticks (i.e rand)
     * need to scale everything to match the proper size, however morphs inherit size from its parent,
     * so there's no need to scale everything again.
     *
     * I also added scaling of TubeComp vect_info because we need to use this for checking
     * whether certain limbs are in RF or not.
     */
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
            if (!res) {
                System.err.println("FAIL AT OBJECT MERGE");
                return false;
            }
        }

        // 3. general smooth afterward
        nowObj.smoothVertexAndNormMat(6, 15); // smooth the vertex by 4 times. normal by 10times



        this.setObj1(MObj[1]);
        this.getObj1().rotateMesh(getFinalRotation());

        //Shift back to (0,0)
        Point3d shiftVec = getMassCenter();
        getObj1().translateFwd(shiftVec);
        this.getObj1().scaleTheObj(getScaleForMAxisShape()); //AC: IMPORTANT CHANGE
        getObj1().translateBack(shiftVec);


        if (isDoCenterObject()) {
            setFinalShiftinDepth(this.getObj1().subCenterOfMass());
        }

        //AC addition for RF relative positioning: scale the comp vect_info as well.
        //We do the scaling here instead of relying on TubeComp to do it because
        //tubecomp will only do it during drawSurfPt, but we want to be able to rely
        //on this information being accurate before and if we don't call drawSurfPt.
        //If we are properly calling RadAppliedFactory then we don't have to worry about keeping this
        //information stable for smoothing the next morph of this mStick.
        for (i = 1; i <= getnComponent(); i++) {
            getComp()[i].setScaleOnce(false); //don't scale it again when drawSurfPt is called because we do it here
            Point3d[] vect_info = getComp()[i].getVect_info();
            for (Point3d point : vect_info) {
                if (point != null) {
                    point.sub(shiftVec);
                    point.scale(getScaleForMAxisShape());
                    point.add(shiftVec);
                }
            }
        }


        return true;
    }



}