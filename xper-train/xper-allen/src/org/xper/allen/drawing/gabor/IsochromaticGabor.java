package org.xper.allen.drawing.gabor;

import org.lwjgl.opengl.GL11;
import org.xper.drawing.Context;
import org.xper.rfplot.drawing.GratingSpec;

public class IsochromaticGabor extends Gabor{
    GratingSpec spec;

    @Override
    public void draw(Context context) {
        GL11.glEnable(GL11.GL_TEXTURE_2D);
        GL11.glBindTexture(GL11.GL_TEXTURE_2D, textureId); // Bind the texture

        GL11.glPushMatrix();
        GL11.glTranslatef(0.0f, 0.0f, 0.0f);

        GL11.glBegin(GL11.GL_QUADS);

        for (int i = 0; i < STEPS; i++) {
            float phase = (float) spec.getPhase();
            float frequency = (float) spec.getFrequency();
            float modFactor = (float) ((Math.sin(2.0 * Math.PI * frequency * (i / (float) STEPS) + phase) + 1.0) / 2.0);
            float size = (float) spec.getSize();

            float r = 1.0f * modFactor; // Use modulated intensity for color
            float g = 1.0f * modFactor;
            float b = 1.0f * modFactor;

            // Texture coordinates
            float tx1 = 0.0f, tx2 = 1.0f;
            float ty1 = (float)i / STEPS, ty2 = (float)(i+1) / STEPS;

            GL11.glColor3f(r, g, b); // Optional if you want to modulate texture with color

            // Bottom Left
            GL11.glTexCoord2f(tx1, ty1);
            GL11.glVertex2f(-size, -size + 2 * size * i / STEPS);

            // Bottom Right
            GL11.glTexCoord2f(tx2, ty1);
            GL11.glVertex2f(size, -size + 2 * size * i / STEPS);

            // Top Right
            GL11.glTexCoord2f(tx2, ty2);
            GL11.glVertex2f(size, -size + 2 * size * (i + 1) / STEPS);

            // Top Left
            GL11.glTexCoord2f(tx1, ty2);
            GL11.glVertex2f(-size, -size + 2 * size * (i + 1) / STEPS);
        }

        GL11.glEnd();
        GL11.glPopMatrix();

        GL11.glDisable(GL11.GL_TEXTURE_2D); // Disable texture if not used afterwards
    }

    public GratingSpec getSpec() {
        return spec;
    }

    public void setSpec(GratingSpec spec) {
        this.spec = spec;
    }
}