package org.xper.allen.drawing.ga;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.utils.Lighting;

import javax.vecmath.Point3d;
import java.nio.FloatBuffer;

/**
 * A {@link GAMatchStick} rendered under a configurable light position.
 *
 * The base {@code MatchStick.initLight()} hardcodes the OpenGL light at {0, 0, 500, 1}. This
 * subclass overrides it so the same shape can be re-rendered from a different lighting
 * direction (used by the LightingSideTest via LightingGAStim). When no light is supplied it
 * falls back to the same {0, 0, 500, 1} default, so it behaves identically to a normal stim.
 */
public class LightingGAMatchStick extends GAMatchStick {

    public static final float[] DEFAULT_LIGHT_POSITION = {0.0f, 0.0f, 500.0f, 1.0f};

    private float[] lightPosition = DEFAULT_LIGHT_POSITION;

    public LightingGAMatchStick(Point3d centerOfMassLocation, float[] lightPosition) {
        super(centerOfMassLocation);
        if (lightPosition != null) {
            this.lightPosition = lightPosition;
        }
    }

    @Override
    protected void initLight() {
        // Mirrors MatchStick.initLight(), differing only in that the light position comes from
        // lightPosition rather than a hardcoded {0, 0, 500, 1}.
        if (textureType.compareTo("2D") == 0) {
            getObj1().setDoLighting(false);
            getObj1().getStimColor().setRed((float) (getStimColor().getRed() * contrast));
            getObj1().getStimColor().setBlue((float) (getStimColor().getBlue() * contrast));
            getObj1().getStimColor().setGreen((float) (getStimColor().getGreen() * contrast));
        } else {
            getObj1().setDoLighting(true);
        }

        Lighting light = new Lighting();
        light.setLightColor(getStimColor());
        light.setTextureType(textureType);

        float[] mat_ambient = light.getAmbient();
        float[] mat_diffuse = light.getDiffuse();
        float[] mat_specular = light.getSpecular();
        float mat_shininess = light.getShine();

        getObj1().contrast = contrast;

        FloatBuffer mat_specularBuffer = BufferUtils.createFloatBuffer(mat_specular.length);
        mat_specularBuffer.put(mat_specular).flip();

        FloatBuffer mat_ambientBuffer = BufferUtils.createFloatBuffer(mat_ambient.length);
        mat_ambientBuffer.put(mat_ambient).flip();

        FloatBuffer mat_diffuseBuffer = BufferUtils.createFloatBuffer(mat_diffuse.length);
        mat_diffuseBuffer.put(mat_diffuse).flip();

        FloatBuffer light_positionBuffer = BufferUtils.createFloatBuffer(lightPosition.length);
        light_positionBuffer.put(lightPosition).flip();

        GL11.glMaterial(GL11.GL_FRONT, GL11.GL_SPECULAR, mat_specularBuffer);
        GL11.glMaterialf(GL11.GL_FRONT, GL11.GL_SHININESS, mat_shininess);
        GL11.glMaterial(GL11.GL_FRONT, GL11.GL_AMBIENT, mat_ambientBuffer);
        GL11.glMaterial(GL11.GL_FRONT, GL11.GL_DIFFUSE, mat_diffuseBuffer);

        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_POSITION, light_positionBuffer);

        // make sure white light
        float[] white_light = {1.0f, 1.0f, 1.0f, 1.0f};
        FloatBuffer wlightBuffer = BufferUtils.createFloatBuffer(white_light.length);
        wlightBuffer.put(white_light).flip();
        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_DIFFUSE, wlightBuffer);
        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_SPECULAR, wlightBuffer);

        GL11.glEnable(GL11.GL_LIGHT0);
    }
}
