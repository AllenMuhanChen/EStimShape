package org.xper.rfplot.drawing.gabor;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.ArrayList;
import java.util.List;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.drawing.DefaultSpecRFPlotDrawable;
import org.xper.rfplot.drawing.GaborSpec;

public class Gabor extends DefaultSpecRFPlotDrawable {
    protected static int STEPS = 5000;
    protected ByteBuffer array;
    protected int textureId = -1;

    private GaborSpec gaborSpec = new GaborSpec();
    protected int w;
    protected int h;
    protected double frequencyCyclesPerMm;
    protected float verticalPosition;
    protected float phase;
    protected int stepsPerHalfCycle;

    public Gabor() {
//        this.array = ByteBuffer.allocateDirect(STEPS * (3 + 2 + 3) * 4 * Float.SIZE / 8)
//                .order(ByteOrder.nativeOrder());
        setDefaultSpec();
//        stepsPerHalfCycle = 256;
        stepsPerHalfCycle = 25;
    }

    protected void initTexture(Context context) {
        double diameterDeg = getGaborSpec().getDiameter(); // Gabor patch diameter in degrees of visual angle
        double diameterMm = context.getRenderer().deg2mm(diameterDeg); // Convert diameter from degrees to millimeters

        // Calculate the fraction of the viewport width occupied by the Gabor patch in mm
        double viewportWidthMm = context.getRenderer().getVpWidthmm(); // Viewport width in millimeters
        double fractionOfViewportWidthMm = diameterMm / viewportWidthMm;

        // Since the normalized coordinate system spans 2 units (-1 to 1), calculate the normalized diameter
        double normalizedDiameter = fractionOfViewportWidthMm;

        // Specify the percentage of the diameter where the fade strength should be 3 sigmas
        double fadePercentOfDiameter = 0.5;

        // Calculate the number of sigmas based on the specified percentage of diameter
        int nSigmas = (int) Math.ceil(2 / (2 * fadePercentOfDiameter));

        // Calculate sigma as a fraction of the normalized diameter, divided by the desired number of sigmas
        // Here, sigma represents the spread of the Gaussian in terms of the normalized coordinate system
        double normalizedSigma = (normalizedDiameter / 2) / nSigmas;

        ByteBuffer texture = makeTexture(w, h, normalizedDiameter, normalizedSigma); // Adjust w, h, std as needed
        textureId = GL11.glGenTextures(); // Generate texture ID
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureId);

        GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 1);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_ALPHA, w, h, 0, GL11.GL_ALPHA, GL11.GL_FLOAT, texture);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
        GL11.glTexEnvf(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_MODULATE);
    }

    @Override
    public void draw(Context context) {

        Gabor.initGL(context.getRenderer().getVpWidth(), context.getRenderer().getVpHeight());
        w = context.getRenderer().getVpWidth(); //in pixels
        h = context.getRenderer().getVpHeight(); //in pixels


        GL11.glPushMatrix();
        GL11.glMatrixMode(GL11.GL_MODELVIEW);

        translateGrating(context);
        rotateGrating();
        bindGaussianTexture(context);
        drawGabor(context);

        if (getGaborSpec().isAnimation()){
            getGaborSpec().setPhase(getGaborSpec().getPhase() + 0.1);
        }
    }

    private void drawGabor(Context context) {
        GL11.glBegin(GL11.GL_QUADS);

        phase = (float) getGaborSpec().getPhase();

        // Convert frequency from cycles per degree to cycles per mm
        float frequencyCyclesPerDegree = (float) getGaborSpec().getFrequency();
        frequencyCyclesPerMm = frequencyCyclesPerDegree / context.getRenderer().deg2mm(1.0);

        System.out.println("stepsPerHalfCycle " + stepsPerHalfCycle);
        STEPS = calcNumSteps(frequencyCyclesPerDegree, stepsPerHalfCycle);
//        STEPS = calcNumSteps(context);
        System.out.println("STEPS: " + STEPS);

        float heightMm = (float) context.getRenderer().deg2mm(getGaborSpec().getDiameter()*3);
        float widthMm = heightMm;
        float widthVp = (float) context.getRenderer().getVpWidthmm();
        float heightVp = (float) context.getRenderer().getVpHeightmm();

        for (int i = 0; i < STEPS; i++) {
            verticalPosition = -heightMm + 2*heightMm * (i / (float) STEPS);
            float modFactor = calcModFactor(i, STEPS);
            float[] rgb = modulateColor(modFactor);


            // Texture coordinates: between 0-1, where 0 is the left edge of the texture
            float distanceLeftGaborMm = (widthVp - widthMm) / 2; // distance from left of viewport to left of Gabor patch in mm
            float tx1 = distanceLeftGaborMm / widthVp; // distance from left of viewport to left of Gabor patch as a ratio of whole viewport
            float tx2 = (distanceLeftGaborMm + widthMm) / widthVp; // distance from left of viewport to right of Gabor patch as a ratio of whole viewport
            float gaborHeightMm =  ((float) i / (STEPS-1)) * heightMm; // height of the part of the gabor patch being drawn in mm
            float distanceUnderGaborMm = (heightVp - heightMm) / 2; // distance from bottom of viewport to bottom of Gabor patch in mm
            float ty1 = (gaborHeightMm + distanceUnderGaborMm) / heightVp; // distance from bottom of viewport to bottom of Gabor patch as a ratio of whole viewport
            float ty2 = (gaborHeightMm + distanceUnderGaborMm + ((float) 1 / STEPS) * heightMm) / heightVp; // distance from bottom of viewport to the hieght of next of part of the patch as a ratio of whole viewport


            GL11.glColor3f(rgb[0], rgb[1], rgb[2]);

            // Bottom Left
            GL11.glTexCoord2f(tx1, ty1);
            GL11.glVertex2f(-widthMm, -heightMm + 2 * heightMm * i / (STEPS-1));

            // Bottom Right
            GL11.glTexCoord2f(tx2, ty1);
            GL11.glVertex2f(widthMm, -heightMm + 2 * heightMm * i / (STEPS-1));

            // Top Right
            GL11.glTexCoord2f(tx2, ty2);
            GL11.glVertex2f(widthMm, -heightMm + 2 * heightMm * (i + 1) / (STEPS-1));

            // Top Left
            GL11.glTexCoord2f(tx1, ty2);
            GL11.glVertex2f(-widthMm, -heightMm + 2 * heightMm * (i + 1) / (STEPS-1));
        }

        GL11.glEnd();
        GL11.glPopMatrix();

        GL11.glDisable(GL11.GL_TEXTURE_2D); // Disable texture if not used afterwards
    }

    /**
     * Calculate the number of steps needed to draw the Gabor patch given the frequency of cycles and steps per cycle.
     *
     * The total size of grating drawn is 2 * diameter, and since
     *
     * We
     * @param frequencyCyclesPerDegree
     * @param stepsPerHalfCycle
     * @return
     */
    protected int calcNumSteps(float frequencyCyclesPerDegree, int stepsPerHalfCycle) {
        double totalGratingSizeDegrees = getGaborSpec().getDiameter() * 2;
        int stepsPerCycle = 2 * stepsPerHalfCycle;
        return (int) (frequencyCyclesPerDegree * totalGratingSizeDegrees * stepsPerCycle);
    }

    protected int calcNumSteps(Context context){
        double totalGratingSizeDegrees = getGaborSpec().getDiameter() * 3;
        double totalSizeMm = context.getRenderer().deg2mm(totalGratingSizeDegrees);
        double widthMm = context.getRenderer().getVpWidthmm(); //
        System.out.println("widthMm: " + widthMm);
        double widthPixels = context.getRenderer().getVpWidth(); //in pixels
        System.out.println("widthPixels: " + widthPixels);
        double pixelsPerMm = widthPixels / widthMm;
        return (int) Math.round((totalSizeMm * pixelsPerMm) * 2);
    }

    protected float calcModFactor(float i, int STEPS){
        return (float) ((Math.sin(2 * Math.PI * frequencyCyclesPerMm * (verticalPosition + phase)) + 1) / 2);
    }

    protected void bindGaussianTexture(Context context) {
        // Only make the texture if it hasn't been made yet or we need to recalculate it
        if (textureId == -1)
            initTexture(context);
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureId); // Bind the texture
    }

    private void translateGrating(Context context) {
        //Translate the patch to the xCenter and yCenter specified
        double xCenterMm = context.getRenderer().deg2mm(getGaborSpec().getXCenter());
        double yCenterMm = context.getRenderer().deg2mm(getGaborSpec().getYCenter());
        GL11.glTranslatef((float) xCenterMm, (float) yCenterMm, 0.0f);
    }

    private void rotateGrating() {
        // Rotate the patch according to the spec's orientation
        float orientationDegrees = (float) getGaborSpec().getOrientation();
        GL11.glRotatef(orientationDegrees, 0.0f, 0.0f, 1.0f);
    }

    @Override
    public void setDefaultSpec() {
        setGaborSpec(new GaborSpec());
        getGaborSpec().setPhase(0);
        getGaborSpec().setFrequency(1);
        getGaborSpec().setOrientation(0);
        getGaborSpec().setAnimation(true);
        getGaborSpec().setSize(5);
        getGaborSpec().setXCenter(0);
        getGaborSpec().setYCenter(0);
        getGaborSpec().setColor(new RGBColor(1, 0, 0));
    }

    protected float[] modulateColor(float modFactor) {
        float r = getGaborSpec().getColor().getRed() * modFactor; // Use modulated intensity for color
        float g = getGaborSpec().getColor().getGreen() * modFactor;
        float b = getGaborSpec().getColor().getBlue() * modFactor;
        float[] rgb = {r, g, b};
        return rgb;
    }

    protected ByteBuffer makeTexture(int w, int h, double diskDiameter, double std) {
        ByteBuffer texture = ByteBuffer.allocateDirect(w * h * Float.SIZE / 8).order(ByteOrder.nativeOrder());

        double circleRadius = diskDiameter/4; // Specify the radius of the disk where the texture is shown normally
        //we divide by four because one division by two converts to radius,
        //and another because the coordinate system we use here is -1 to 1, but the diameter
        //is specified as 0-1. So we divide by 2 to get the radius in the -1 to 1 coordinate system.

        double diskAlpha = 1.0; // Specify the alpha level within the disk

        double aspectRatio = (double) w / h;
        for (int i = 0; i < h; i++) {
            double y = ((double) i / (h - 1) * 2 - 1) / aspectRatio; // Adjust y-coordinate by aspect ratio
            for (int j = 0; j < w; j++) {
                double x = ((double) j / (w - 1) * 2 - 1);
                double distanceToCenter = Math.sqrt(x * x + y * y);

                float n;

                if (distanceToCenter <= circleRadius) {
                    // Within the disk
                    n = (float) diskAlpha;
                } else {
                    // Calculate Gaussian fade from the disk's edge
                    double offsetDistance = distanceToCenter - circleRadius;
                    double gaussValue = diskAlpha * Math.exp(-0.5 * (Math.pow(offsetDistance / std, 2)));
                    n = (float) Math.min(gaussValue, 1.0);
                }

                texture.putFloat(n);
            }
        }
        texture.flip();
        return texture;
    }

//    protected ByteBuffer makeTexture(int w, int h, double std) {
//        ByteBuffer texture = ByteBuffer.allocateDirect(w * h * Float.SIZE / 8).order(ByteOrder.nativeOrder());
//        double aspectRatio = (double) w / h;
//        NormalDistribution distribution = new NormalDistribution(0, std);
//        double norm_max = distribution.density(0);
//
//        for (int i = 0; i < h; i++) {
//            double y = ((double) i / (h - 1) * 2 - 1) / aspectRatio; // Adjust x-coordinate by aspect ratio
//            for (int j = 0; j < w; j++) {
//                double x = ((double) j / (w - 1) * 2 - 1);
//                double dist = Math.sqrt(y * y + x * x);
//                float n = (float) (distribution.density(dist) / norm_max);
//                texture.putFloat(n);
//            }
//        }
//        texture.flip();
//        return texture;
//    }

    public static double normal(double mean, double standardDeviation) {
        double x = Math.random();
        double y = Math.random();
        double z = Math.sqrt(-2.0 * Math.log(x)) * Math.cos(2.0 * Math.PI * y);
        return mean + standardDeviation * z;
    }

    public void setSpec(String spec) {
        recalculateTextureIfChangeSigma(spec);
        this.setGaborSpec(IsoGaborSpec.fromXml(spec));

    }

    private void recalculateTextureIfChangeSigma(String spec) {
        String oldSpec = getSpec();
        IsoGaborSpec oldGabor = IsoGaborSpec.fromXml(oldSpec);
        double oldSigma = oldGabor.getDiameter();
        double newSigma = IsoGaborSpec.fromXml(spec).getDiameter();
        if (oldSigma != newSigma) {
            recalculateTexture();
        }
    }

    protected void recalculateTexture(){
        this.textureId = -1;
    }


    public static void initGL(int w, int h) {
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glShadeModel(GL11.GL_SMOOTH);
    }



    @Override
    public List<Coordinates2D> getOutlinePoints(AbstractRenderer renderer) {
        int numberOfPoints = 5 + (int) (getGaborSpec().getDiameter() * 3);
        List<Coordinates2D> profilePoints = new ArrayList<>();

        // The radius for the circle of points around the mouse position
        double radius = (getGaborSpec().getDiameter()*2) / 2; // Half the effective diameter of the Gabor patch
        // it has diameter, and half diameter fade on all sides, so we multiply by 2 to get the full diameter
        double radiusMm = renderer.deg2mm(radius);
        // Calculate the angle increment for evenly distributing points around the circle
        double angleIncrement = 2 * Math.PI / numberOfPoints;

        for (int i = 0; i < numberOfPoints; i++) {
            // Calculate the angle for this point
            double angle = angleIncrement * i;

            // Calculate the coordinates for this point, centered around the mouse position
            double newX = Math.cos(angle) * radiusMm;
            double newY = Math.sin(angle) * radiusMm;

            // Add the new point to the list of profile points
            profilePoints.add(new Coordinates2D(newX, newY));
        }

        return profilePoints;
    }

    @Override
    public String getOutputData() {
        return gaborSpec.toXml();
    }

    public String getSpec() {
        return getGaborSpec().toXml();
    }

    public void setGaborSpec(GaborSpec gaborSpec) {
        this.gaborSpec = gaborSpec;
    }
    public GaborSpec getGaborSpec() {
        return gaborSpec;
    }

}