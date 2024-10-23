package org.xper.allen.pga.alexnet;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.JunctionData;
import org.xper.allen.drawing.composition.ShaftData;
import org.xper.allen.drawing.composition.TerminationData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.utils.Lighting;

import javax.vecmath.Point3d;
import java.nio.FloatBuffer;
import java.util.List;

public class AlexNetGAMAtchStick extends MorphedMatchStick {

    public float[] light_position;
    public Coordinates2D location;
    public double size;

    public AlexNetGAMAtchStick(float[] light_position, RGBColor stimColor, Coordinates2D location, double size, String textureType) {
        this.light_position = light_position;
        this.location = location;
        this.setScaleForMAxisShape(size);
        setTextureType(textureType);
        setStimColor(stimColor);
        setContrast(0.5);

    }

    protected void initLight() {
        if (textureType.compareTo("2D") == 0) {
            getObj1().contrast = contrast;
            getObj1().doLighting = false;
            getObj1().getStimColor().setRed((float)(stimColor.getRed()*contrast));
            getObj1().getStimColor().setBlue((float)(stimColor.getBlue()*contrast));
            getObj1().getStimColor().setGreen((float)(stimColor.getGreen()*contrast));
        } else {
            getObj1().doLighting = true;
        }

        Lighting light = new Lighting();
        light.setLightColor(stimColor);
        light.setTextureType(textureType);

        float[] mat_ambient = light.getAmbient();
        float[] mat_diffuse = light.getDiffuse();
        float[] mat_specular = light.getSpecular();
        float mat_shininess = light.getShine();




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

    protected void positionShape(){
        moveCenterOfMassTo(new Point3d(location.getX(), location.getY(), 0));
    }

    /**
     * Compares to mass center rather 0,0
     * @return
     */
    @Override
    protected boolean validMStickSize()
    {
        double screenDist = 500;
        double maxDiameterPixels = getScaleForMAxisShape(); // DIAMETER in degrees
        double radiusMm = degToMm(maxDiameterPixels, screenDist) / 2;
        int i, j;

        Point3d ori = getMassCenter();
//		Point3d ori = new Point3d(0,0,0);
        double dis;
        for (i=1; i<=getnComponent(); i++)
            for (j=1; j<= getComp()[i].getnVect(); j++) {
                dis = getComp()[i].getVect_info()[j].distance(ori);
                if ( dis > radiusMm ) {
                    return false;
                }
            }
        return true;
    }

    public AlexNetGAMStickData getMStickData(){
        modifyMStickFinalInfoForAnalysis();
        AllenMStickSpec analysisMStickSpec = new AllenMStickSpec();
        analysisMStickSpec.setMStickInfo(this, false);


        Point3d massCenter = getMassCenter();

        List<ShaftData> shaftData = calculateShaftData();
        List<TerminationData> terminationData = calculateTerminationData();
        List<JunctionData> junctionData = calculateJunctionData();

        return new AlexNetGAMStickData(shaftData,
                terminationData,
                junctionData,
                analysisMStickSpec,
                massCenter,
                light_position,
                stimColor,
                location,
                size);
    }


}