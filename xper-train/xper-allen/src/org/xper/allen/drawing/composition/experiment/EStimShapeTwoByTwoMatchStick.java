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
    protected void positionShape() throws MorphedMatchStick.MorphException {
        RFUtils.positionAroundRF(rfStrategy, this, rf);
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