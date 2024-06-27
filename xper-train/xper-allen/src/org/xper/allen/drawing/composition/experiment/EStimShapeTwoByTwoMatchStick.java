package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point3d;
import java.util.List;

public class EStimShapeTwoByTwoMatchStick extends TwobyTwoMatchStick{

    private final RFStrategy rfStrategy;
    private final ReceptiveField rf;


    public EStimShapeTwoByTwoMatchStick(RFStrategy rfStrategy, ReceptiveField rf) {
        this.rfStrategy = rfStrategy;
        this.rf = rf;
        this.noiseRadiusMm = rf.radius*2;
    }

    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
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



}