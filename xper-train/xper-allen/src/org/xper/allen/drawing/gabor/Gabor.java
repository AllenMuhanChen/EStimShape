package org.xper.allen.drawing.gabor;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.rfplot.drawing.GratingSpec;
import org.xper.util.MathUtil;

public class Gabor implements Drawable {
    protected static final int STEPS = 1024;
    protected ByteBuffer array;
    protected int textureId;

    GratingSpec spec;
    private int w;
    private int h;

    public Gabor() {
        this.array = ByteBuffer.allocateDirect(STEPS * (3 + 2 + 3) * 4 * Float.SIZE / 8)
                .order(ByteOrder.nativeOrder());

    }

    private void initTexture(Context context) {
        w = context.getRenderer().getVpWidth(); //in pixels
        h = context.getRenderer().getVpHeight(); //in pixels

        double diameterDeg = spec.getSize();
        double diameterMm = context.getRenderer().deg2mm(diameterDeg);
        double sigma = diameterMm/context.getRenderer().getWidth() / 6.0; //we want ~99.7% of gabor to be within the size we specify



        ByteBuffer texture = makeTexture(w, h, sigma); // Adjust w, h, std as needed
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


        initTexture(context);

        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureId); // Bind the texture

        GL11.glPushMatrix();
        GL11.glTranslatef(0.0f, 0.0f, 0.0f);

        GL11.glBegin(GL11.GL_QUADS);


        float phase = (float) spec.getPhase();
        // Frequency in cycles per degree.
        float frequencyCyclesPerDegree = (float) spec.getFrequency();
        // Convert frequency to cycles per millimeter.
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

    protected float[] modulateColor(float modFactor) {
        float r = 1.0f * modFactor; // Use modulated intensity for color
        float g = 1.0f * modFactor;
        float b = 1.0f * modFactor;
        float[] rgb = {r, g, b};
        return rgb;
    }

    /**
     *
     * @param w: width of viewport in pixels
     * @param h: height of viewport in pixels
     * @param std: standard deviation of the Gaussian as a fraction (independent of the size of the viewport)
     * @return
     */
    protected static ByteBuffer makeTexture(int w, int h, double std) {
        ByteBuffer texture = ByteBuffer.allocateDirect(w * h * Float.SIZE / 8).order(ByteOrder.nativeOrder());
        double norm_max = MathUtil.normal(0, 0, std);

        for (int i = 0; i < w; i++) {
            double x = (double) i / (w - 1) * 2 - 1;
            for (int j = 0; j < h; j++) {
                double y = (double) j / (h - 1) * 2 - 1;
                double dist = Math.sqrt(x * x + y * y);
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

    public GratingSpec getSpec() {
        return spec;
    }

    public void setSpec(GratingSpec spec) {
        this.spec = spec;
    }
}