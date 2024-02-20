package org.xper.allen.drawing.gabor;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.drawing.Drawable;
import org.xper.util.MathUtil;

public abstract class Gabor implements Drawable {
    protected static final int STEPS = 1024;
    protected ByteBuffer array;
    protected int textureId;

    public Gabor() {
        this.array = ByteBuffer.allocateDirect(STEPS * (3 + 2 + 3) * 4 * Float.SIZE / 8)
                .order(ByteOrder.nativeOrder());
        initTexture();
    }

    private void initTexture() {
        ByteBuffer texture = makeTexture(1024, 1024, 0.3f); // Adjust w, h, std as needed
        textureId = GL11.glGenTextures(); // Generate texture ID
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureId);

        GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 1);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_ALPHA, 1024, 1024, 0, GL11.GL_ALPHA, GL11.GL_FLOAT, texture);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
        GL11.glTexEnvf(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_MODULATE);
    }

    public abstract void draw(Context context);

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
        ByteBuffer texture = makeTexture(w, h, 0.3f); // Example standard deviation for Gabor

        GL11.glPixelStorei(GL11.GL_UNPACK_ALIGNMENT, 1);
        GL11.glTexImage2D(GL11.GL_TEXTURE_2D, 0, GL11.GL_ALPHA, w, h, 0, GL11.GL_ALPHA, GL11.GL_FLOAT, texture);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_S, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_WRAP_T, GL11.GL_CLAMP);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MAG_FILTER, GL11.GL_NEAREST);
        GL11.glTexParameterf(GL11.GL_TEXTURE_2D, GL11.GL_TEXTURE_MIN_FILTER, GL11.GL_NEAREST);
        GL11.glTexEnvf(GL11.GL_TEXTURE_ENV, GL11.GL_TEXTURE_ENV_MODE, GL11.GL_MODULATE);
        GL11.glEnable(GL11.GL_BLEND);
        GL11.glBlendFunc(GL11.GL_SRC_ALPHA, GL11.GL_ONE_MINUS_SRC_ALPHA);
        GL11.glShadeModel(GL11.GL_SMOOTH);
    }
}