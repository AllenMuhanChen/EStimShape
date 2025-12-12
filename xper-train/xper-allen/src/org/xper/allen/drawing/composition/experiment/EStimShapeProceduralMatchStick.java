package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NAFCNoiseMapper;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point2d;
import javax.vecmath.Point3d;
import java.util.*;

/**
 * DEPRECATED.... this used to uniquely implement rf behavior for procedural stim... but now procedural match sticks
 * subclass GAMatchSTick which contains rf behavior.
 * MatchSticks that are used to generate stimuli for the EStimShape NAFC Experiment.
 *
 * Includes:
 * 1. the ability to generate mSticks from base components and generate delta trials.
 * 2. partially or completely inside Receptive Field behavior based on special limb.
 *
 */
public class EStimShapeProceduralMatchStick extends ProceduralMatchStick {

    public EStimShapeProceduralMatchStick(RFStrategy rfStrategy, ReceptiveField rf, NAFCNoiseMapper noiseMapper) {
        super(noiseMapper);
        this.rfStrategy = rfStrategy;
        this.rf = rf;
        this.noiseRadiusMm = rf.radius*3;
    }


    @Override
    public void drawCompMap(){
        if (noiseDebugMode) {
            draw_debug_gaussian_mapper();
            drawNoise();
            return;
        }

        super.drawCompMap();


        drawRF();
        drawNoise();
    }

    private void drawNoise() {
        double radius = noiseRadiusMm;

        Point3d noiseOrigin = this.getNoiseOrigin();
        if (noiseOrigin == null) {
            return;
        }
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

    }

    /**
     * deprecrated
     */
    private void draw_debug_gaussian_mapper() {
        if(noiseMapper!=null){
            //ALL POINTS FROM THE OBJ1
//            GL11.glColor4f(1.0f, 1.0f, 0.0f, 0.5f);
//            List<Point2d> pointsToDraw = ((GaussianNoiseMapper) noiseMapper).debug_points_obj1;
//            for (Point2d point : pointsToDraw) {
//                GL11.glPointSize(0.1f);
//                GL11.glBegin(GL11.GL_POINTS);
//                GL11.glVertex2d(point.x, point.y);
//                GL11.glEnd();
//            }

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
    public void positionShape() throws MorphException {
        RFUtils.positionAroundRF(rfStrategy, this, rf, 100);
    }

    @Override
    public void drawRF() {
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