package org.xper.rfplot.drawing.gabor;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.rfplot.drawing.DefaultSpecRFPlotDrawable;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.util.MathUtil;

public class Gabor extends DefaultSpecRFPlotDrawable {
    protected static final int STEPS = 1024;
    protected ByteBuffer array;
    protected int textureId;

    private GaborSpec gaborSpec;
    private int w;
    private int h;

    public Gabor() {
        this.array = ByteBuffer.allocateDirect(STEPS * (3 + 2 + 3) * 4 * Float.SIZE / 8)
                .order(ByteOrder.nativeOrder());

    }

    private void initTexture(Context context) {
        int nSigmas = 6; // Number of standard deviations you want the diameter to span
        double diameterDeg = getGaborSpec().getSize(); // Gabor patch diameter in degrees of visual angle
        double diameterMm = context.getRenderer().deg2mm(diameterDeg); // Convert diameter from degrees to millimeters

        // Calculate the fraction of the viewport width occupied by the Gabor patch in mm
        double viewportWidthMm = context.getRenderer().getVpWidthmm(); // Viewport width in millimeters
        double fractionOfViewportWidthMm = diameterMm / viewportWidthMm;

        // Since the normalized coordinate system spans 2 units (-1 to 1), calculate the normalized diameter
        double normalizedDiameter = fractionOfViewportWidthMm * 2;

        // Calculate sigma as a fraction of the normalized diameter, divided by the desired number of sigmas
        // Here, sigma represents the spread of the Gaussian in terms of the normalized coordinate system
        double normalizedSigma = (normalizedDiameter / 2) / nSigmas; // Divide by 2 to get radius as sigma is based on radius, not diameter

        ByteBuffer texture = makeTexture(w, h, normalizedSigma); // Adjust w, h, std as needed
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

    private double degreesToPixels(double diameterDeg, AbstractRenderer renderer) {
        return renderer.mm2pixel(new Coordinates2D(renderer.mm2deg(diameterDeg), renderer.mm2deg(diameterDeg))).getX();
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

        float phase = (float) getGaborSpec().getPhase();

        // Convert frequency from cycles per degree to cycles per mm
        float frequencyCyclesPerDegree = (float) getGaborSpec().getFrequency();
        double frequencyCyclesPerMm = frequencyCyclesPerDegree / context.getRenderer().deg2mm(1.0);

        for (int i = 0; i < STEPS; i++) {
            float heightMm = (float) context.getRenderer().getVpHeightmm();
            float widthMm = (float) context.getRenderer().getVpWidthmm();
            // Adjusting the modFactor calculation for the frequency across the viewport in mm
            // Assuming the Gabor pattern should span the entire height of the viewport uniformly
            float verticalPosition = -heightMm + 2*heightMm * (i / (float) STEPS);

            float modFactor = (float) ((Math.sin(2.0 * Math.PI * frequencyCyclesPerMm * verticalPosition + phase) + 1.0) / 2.0);

            float[] rgb = modulateColor(modFactor);

            // Texture coordinates
            float tx1 = 0.0f, tx2 = 1.0f;
            float ty1 = (float)i / STEPS, ty2 = (float)(i+1) / STEPS;

            GL11.glColor3f(rgb[0], rgb[1], rgb[2]);

            // Bottom Left
            GL11.glTexCoord2f(tx1, ty1);
            GL11.glVertex2f(-widthMm, -heightMm + 2 * heightMm * i / STEPS);

            // Bottom Right
            GL11.glTexCoord2f(tx2, ty1);
            GL11.glVertex2f(widthMm, -heightMm + 2 * heightMm * i / STEPS);

            // Top Right
            GL11.glTexCoord2f(tx2, ty2);
            GL11.glVertex2f(widthMm, -heightMm + 2 * heightMm * (i + 1) / STEPS);

            // Top Left
            GL11.glTexCoord2f(tx1, ty2);
            GL11.glVertex2f(-widthMm, -heightMm + 2 * heightMm * (i + 1) / STEPS);
        }

        GL11.glEnd();
        GL11.glPopMatrix();

        GL11.glDisable(GL11.GL_TEXTURE_2D); // Disable texture if not used afterwards
    }

    private void bindGaussianTexture(Context context) {
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
        // Adjust for aspect ratio before rotation
        float aspectRatio = (float)w / h;
        if (aspectRatio != 1.0f) {
            GL11.glScalef(1.0f, aspectRatio, 1.0f); // Normalize the aspect ratio for rotation
        }

        // Rotate the patch according to the spec's orientation
        float orientationDegrees = (float) getGaborSpec().getOrientation();
        GL11.glRotatef(orientationDegrees, 0.0f, 0.0f, 1.0f);

        // Reverse the aspect ratio adjustment after rotation
        if (aspectRatio != 1.0f) {
            GL11.glScalef(1.0f, 1.0f / aspectRatio, 1.0f); // Reverse the normalization
        }
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
    }

    protected float[] modulateColor(float modFactor) {
        float r = 1.0f * modFactor; // Use modulated intensity for color
        float g = 1.0f * modFactor;
        float b = 1.0f * modFactor;
        float[] rgb = {r, g, b};
        return rgb;
    }

    protected static ByteBuffer makeTexture(int w, int h, double std) {
        ByteBuffer texture = ByteBuffer.allocateDirect(w * h * Float.SIZE / 8).order(ByteOrder.nativeOrder());
        double norm_max = MathUtil.normal(0, 0, std);
        double aspectRatio = (double) w / h;

        for (int i = 0; i < h; i++) {
            double y = ((double) i / (h - 1) * 2 - 1) / aspectRatio; // Adjust x-coordinate by aspect ratio
//            System.out.println(y);
            for (int j = 0; j < w; j++) {
                double x = ((double) j / (w - 1) * 2 - 1);
                if (i == 0)
                    System.out.println(x);
                double dist = Math.sqrt(y * y + x * x);
                float n = (float) (MathUtil.normal(dist, 0, std) / norm_max);
                texture.putFloat(n);
            }
        }
        texture.flip();
        return texture;
    }


    public static void initGL(int w, int h) {
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glShadeModel(GL11.GL_SMOOTH);
    }

    public String getSpec() {
        return getGaborSpec().toXml();
    }

    public void setSpec(String spec) {
        this.setGaborSpec(GaborSpec.fromXml(spec));
    }

    public GaborSpec getGaborSpec() {
        return gaborSpec;
    }

    public void setGaborSpec(GaborSpec gaborSpec) {
        this.gaborSpec = gaborSpec;
    }
}