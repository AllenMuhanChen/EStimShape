package org.xper.allen.drawing.ga;

import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import java.io.BufferedReader;
import java.io.FileReader;
import java.util.*;

/**
 * MatchSticks that are used to generate stimuli for the GA Experiment.
 * Includes:
 * 1. Morphing
 * 2. Checking if the shape is inside the Receptive Field partially or completely
 *
 */
public class GAMatchStick extends MorphedMatchStick implements Thumbnailable {

    Point3d toMoveCenterOfMassLocation;
    ReceptiveField rf;


    public GAMatchStick(ReceptiveField rf, RFStrategy rfStrategy) {
        this.rf = rf;
        this.rfStrategy = rfStrategy;
    }

    public GAMatchStick(Point3d centerOfMassLocation){
        this.toMoveCenterOfMassLocation = centerOfMassLocation;
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
        this.rfStrategy = RFStrategy.PARTIALLY_INSIDE;
        positionShape();
    }

    @Override
    public void drawCompMap(){
        super.drawCompMap();

        drawRF();
    }

    @Override
    public void drawThumbnail(double imageWidthMm, double imageHeightMm){
        init();
        try {
            Thread.sleep(100);
        } catch (InterruptedException e) {
            e.printStackTrace();
        }
        GL11.glPushMatrix();
//        centerObjOrRFDependingOnBestFit(imageWidthMm);
        centerRFAndScale(imageWidthMm, imageHeightMm);
        drawSkeleton(false);
        drawRF();
        GL11.glPopMatrix();
    }

    private void centerRFAndScale(double imageWidthMm, double imageHeightMm) {
        double rfDiameter = rf.getRadius() * 2;
        double widthScaleFactor = (imageWidthMm / rfDiameter)/2;
        double heightScaleFactor = (imageHeightMm / rfDiameter)/2;
        GL11.glScaled(widthScaleFactor, heightScaleFactor, 1);
        GL11.glTranslated(-rf.getCenter().getX(), -rf.getCenter().getY(), 0);
    }

    private void centerObjOrRFDependingOnBestFit(double imageWidthMm) {
        Point3d centerMass = this.getMassCenter();
        Point3d[] boundingBox = this.getObj1().getBoundingBox();

        double largestDim = Math.max(boundingBox[1].x - boundingBox[0].x, boundingBox[1].y - boundingBox[0].y);

        double shapeScaleFactor = (imageWidthMm / largestDim) / 2; //scale factor to make largest dim of shape fit 50% of the image
        double rfDiameter = rf.getRadius() * 2;
        double rfScaleFactor = (imageWidthMm / rfDiameter) / 2; //scale factor to make rf fit 50% of the image
        double scaleFactor = Math.max(shapeScaleFactor, rfScaleFactor); //choose the largest zoom
        GL11.glScaled(scaleFactor, scaleFactor, 1);
        GL11.glTranslated(-centerMass.x, -centerMass.y, 0);
    }

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


    @Override
    protected void positionShape() throws MorphException {
        if (rfStrategy != null) {
            RFUtils.positionAroundRF(rfStrategy, this, rf, 1000);
            return;
        }
        if (toMoveCenterOfMassLocation != null){
            moveCenterOfMassTo(toMoveCenterOfMassLocation);
            return;
        }
        throw new IllegalArgumentException("rfStrategy and toMoveCenterOfMassLocation both null");
    }



    public RFStrategy getRfStrategy() {
        return rfStrategy;
    }
}