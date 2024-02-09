package org.xper.allen.drawing.composition.experiment;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.depthposthoc.DepthLightingPostHocComponentMorphParameters;
import org.xper.utils.Lighting;

import java.nio.FloatBuffer;
import java.util.LinkedHashMap;
import java.util.Map;

public class DepthLightingPostHocMatchStick extends ExperimentMatchStick{

    public float[] light_position;

    public DepthLightingPostHocMatchStick(float[] light_position) {
        this.light_position = light_position;
    }

    public DepthLightingPostHocMatchStick() {
        light_position = new float[]{0.0f, 0.0f, 500.0f, 1.0f};
    }

    public void genFlippedMatchStick(DepthLightingPostHocMatchStick baseMStick, int componentId) {
        Map<Integer, ComponentMorphParameters> morphParameters = new LinkedHashMap<>();
        morphParameters.put(componentId, new DepthLightingPostHocComponentMorphParameters());
        this.genMorphedMatchStick(morphParameters, baseMStick);
    }


    protected void positionShape() {

    }

    protected void initLight() {
        if (textureType.compareTo("2D") == 0) {
            getObj1().doLighting = false;
            getObj1().stimColor.setRed((float)(stimColor.getRed()*contrast));
            getObj1().stimColor.setBlue((float)(stimColor.getBlue()*contrast));
            getObj1().stimColor.setGreen((float)(stimColor.getGreen()*contrast));
        } else
            getObj1().doLighting = true;

        Lighting light = new Lighting();
        light.setLightColor(stimColor);
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

        FloatBuffer light_positionBuffer = BufferUtils.createFloatBuffer(light_position.length);
        light_positionBuffer.put(light_position).flip();


        GL11.glMaterial(GL11.GL_FRONT, GL11.GL_SPECULAR, mat_specularBuffer);
        GL11.glMaterialf(GL11.GL_FRONT, GL11.GL_SHININESS, mat_shininess);
        GL11.glMaterial(GL11.GL_FRONT, GL11.GL_AMBIENT, mat_ambientBuffer);
        GL11.glMaterial(GL11.GL_FRONT, GL11.GL_DIFFUSE, mat_diffuseBuffer);

        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_POSITION, light_positionBuffer);

        // make sure white light
        float[] white_light = { 1.0f, 1.0f, 1.0f, 1.0f};
        FloatBuffer wlightBuffer = BufferUtils.createFloatBuffer( white_light.length);
        wlightBuffer.put(white_light).flip();
        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_DIFFUSE, wlightBuffer);
        GL11.glLight(GL11.GL_LIGHT0, GL11.GL_SPECULAR, wlightBuffer);

        GL11.glEnable(GL11.GL_LIGHT0);
    }



}