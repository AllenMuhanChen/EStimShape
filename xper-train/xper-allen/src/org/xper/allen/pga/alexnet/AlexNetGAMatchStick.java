package org.xper.allen.pga.alexnet;

import org.lwjgl.BufferUtils;
import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.*;
import org.xper.allen.drawing.composition.morph.ComponentMorphParameters;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.utils.Lighting;

import javax.vecmath.Point3d;
import java.nio.FloatBuffer;
import java.util.HashSet;
import java.util.List;
import java.util.Map;

import static org.xper.allen.drawing.composition.morph.GrowingMatchStick.*;

public class AlexNetGAMatchStick extends MorphedMatchStick {

    public float[] light_position;
    public Coordinates2D location;
    public double contrast;

    public AlexNetGAMatchStick(float[] light_position, RGBColor stimColor, Coordinates2D location, double size, String textureType, double contrast) {
        this.light_position = light_position;
        this.location = location;
        this.setScaleForMAxisShape(size);
        setTextureType(textureType);
        setStimColor(stimColor);
        setContrast(contrast);
    }

    public void genGrowingMatchStick(AlexNetGAMatchStick parent, double magnitude) {
        //Removing Comps - Non RF operation
        HashSet<Integer> componentsToRemove = specifyCompsToRemove(parent, magnitude);
        AlexNetGAMatchStick componentRemovedMStick = new AlexNetGAMatchStick(light_position, stimColor, location, getScaleForMAxisShape(), textureType, 0.5);

        componentRemovedMStick.genRemovedLimbsMatchStick(parent, componentsToRemove);


        //Morphing Existing Comps - Either NON RF or RF Operation
        Map<Integer, ComponentMorphParameters> paramsForComps = specifyCompMorphParams(componentRemovedMStick, magnitude, 1/3.0);
        AlexNetGAMatchStick morphedMStick = new AlexNetGAMatchStick(light_position, stimColor, location, getScaleForMAxisShape(), textureType, 0.5);
        morphedMStick.genMorphedComponentsMatchStick(paramsForComps, componentRemovedMStick, true);

        //Adding New Comps - NON RF Operation

        int nCompsToAdd = specifyNCompsToAdd(morphedMStick, magnitude);
        genAddedLimbsMatchStick(morphedMStick, nCompsToAdd);
    }

    private HashSet<Integer> specifyCompsToRemove(MorphedMatchStick matchStickToMorph, double magnitude) {
        int currentNComp = matchStickToMorph.getNComponent();
        HashSet<Integer> componentsToRemove = new HashSet<>();

        // Find max and min number of components allowed
        int maxNComp = findMaxIndex(PARAM_nCompDist) + 1;
        int minNComp = findMinIndex(PARAM_nCompDist) + 1;

        // Ensure the min and max are within valid range
        if (minNComp < 1) minNComp = 1;
        if (maxNComp > currentNComp) maxNComp = currentNComp;

        // Calculate the number of components to remove based on a simple strategy
        int componentsToRemoveCount = calculateNCompsToRemove(currentNComp, minNComp, maxNComp, magnitude);
        System.out.println("Removing " + componentsToRemoveCount + " components");
        // Randomly choose components to remove

        while (componentsToRemove.size() < componentsToRemoveCount) {
            int componentId = (int) (Math.random() * currentNComp) + 1; // Assuming component IDs start at 1
            if (matchStickToMorph.getLeafBranch()[componentId]) continue; // Skip if it is a branch
            componentsToRemove.add(componentId);
        }
        return componentsToRemove;
    }

    private int specifyNCompsToAdd(MorphedMatchStick matchStickToMorph, double magnitude) {
        int currentNComp = matchStickToMorph.getNComponent();

        // Find max and min number of components allowed
        int maxNComp = findMaxIndex(PARAM_nCompDist) + 1;
        int minNComp = findMinIndex(PARAM_nCompDist) + 1;

        // Ensure the min and max are within valid range
        if (minNComp < 1) minNComp = 1;
        if (maxNComp < currentNComp) maxNComp = currentNComp; // Adjusted for adding components

        // Determine the maximum number of components that can be added
        int maxComponentsToAdd = maxNComp - currentNComp;

        // If the current number of components is already at or above the max, no components can be added
        if (maxComponentsToAdd <= 0) {
            System.out.println("No components can be added");
            return 0;
        }

        // Calculate the number of components to add
        // For simplicity, let's assume we always aim to add components up to the max,
        // but this logic can be adjusted based on specific needs or distribution patterns.
        int componentsToAdd = calculateNComponentsToAdd(currentNComp, maxNComp, minNComp, magnitude);

        System.out.println("Adding " + componentsToAdd + " components");
        return componentsToAdd;
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
        AllenMStickSpec stickSpec = new AllenMStickSpec();
        stickSpec.setMStickInfo(this, false);
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
                getScaleForMAxisShape(),
                stickSpec,
                textureType,
                contrast);
    }


}