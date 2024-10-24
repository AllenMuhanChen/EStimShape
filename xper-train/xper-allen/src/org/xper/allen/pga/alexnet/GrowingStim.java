package org.xper.allen.pga.alexnet;

import org.xper.drawing.RGBColor;

public class GrowingStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData>{

    private RGBColor stimColor;

    public GrowingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, RGBColor color, float[] light_position, double magnitude) {
        super(generator, parentId, stimId, null, color, null, light_position, 0, magnitude);

    }

    @Override
    public AlexNetGAMatchStick createMStick() {
        //Read the parent properties, including position, size, etc.
        AlexNetGAMStickData parentData = AlexNetGAMStickData.fromXml(generator.getDbUtil().readStimSpec(parentId).getSpec());
        sizeDiameter = parentData.sizeDiameter;
        location = parentData.location;
        textureType = parentData.textureType;
        stimColor = parentData.stimColor;

        //Generate Parent Stick
        AlexNetGAMatchStick parentMStick = new AlexNetGAMatchStick(parentData.light_position, parentData.stimColor, parentData.location, parentData.sizeDiameter, parentData.textureType);
        parentMStick.genMatchStickFromShapeSpec(parentData.stickSpec, new double[]{0,0,0});
        parentMStick.positionShape();


        //Generate Child Stick
        AlexNetGAMatchStick childMStick = new AlexNetGAMatchStick(light_position, stimColor, location, sizeDiameter, textureType);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);

        return childMStick;
    }

}