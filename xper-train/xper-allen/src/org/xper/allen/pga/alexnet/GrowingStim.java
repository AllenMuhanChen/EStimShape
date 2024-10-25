package org.xper.allen.pga.alexnet;

import org.xper.drawing.RGBColor;

public class GrowingStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData>{

    public static final double TOTAL_MAX_CONTRAST_CHANGE = 0.25;
    public static final double PERCENTAGE_MUTATE_2D_3D = 0.25;
    public GrowingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, RGBColor color, float[] light_position, double magnitude) {
        super(generator, parentId, stimId, null, color, null, light_position, 0, magnitude, 0.5);

    }

    @Override
    public AlexNetGAMatchStick createMStick() {
        //Read the parent properties, including position, size, etc.
        AlexNetGAMStickData parentData = AlexNetGAMStickData.fromXml(generator.getDbUtil().readStimSpec(parentId).getSpec());
        sizeDiameter = parentData.sizeDiameter;
        location = parentData.location;
        color = parentData.stimColor;

        //if mutate 2D
        mutate2D3D(parentData);

        if (textureType.equals("2D")){
            mutateContrast(parentData);
        }

        //Generate Parent Stick
        AlexNetGAMatchStick parentMStick = new AlexNetGAMatchStick(parentData.light_position, parentData.stimColor, parentData.location, parentData.sizeDiameter, parentData.textureType, 0.5);
        parentMStick.genMatchStickFromShapeSpec(parentData.stickSpec, new double[]{0,0,0});
        parentMStick.positionShape();


        //Generate Child Stick
        AlexNetGAMatchStick childMStick = new AlexNetGAMatchStick(light_position, color, location, sizeDiameter, textureType, contrast);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);

        return childMStick;
    }

    private void mutate2D3D(AlexNetGAMStickData parentData) {
        if (Math.random() < PERCENTAGE_MUTATE_2D_3D){
            // Turn 2D into either specular or shade
            if (parentData.textureType.equals("2D")){
                textureType = Math.random() < 0.5 ? "SPECULAR" : "SHADE";
            // Turn specular or shade into 2D
            } else {
                textureType = "2D";
            }
        } else {
            textureType = parentData.textureType;
        }
    }

    private void mutateContrast(AlexNetGAMStickData parentData) {
        double parentContrast = parentData.contrast;
        double maxContrastChange = TOTAL_MAX_CONTRAST_CHANGE * magnitude;
        double contrastChange = Math.random() * maxContrastChange;
        //add or subtract contrast
        double newContrast = Math.random() < 0.5 ? parentContrast + contrastChange : parentContrast - contrastChange;
        //ensure contrast is between 0 and 1
        contrast = Math.min(1, Math.max(0, newContrast));
    }

}