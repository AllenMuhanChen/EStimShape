package org.xper.allen.pga.alexnet;

import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class GrowingStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData>{

    public GrowingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, String textureType, RGBColor color, float[] light_position, double magnitude) {
        super(generator, parentId, stimId, textureType, color, null, light_position, 0, magnitude);

    }

    @Override
    public AlexNetGAMatchStick createMStick() {
        //Read the parent properties, including position, size, etc.
        AlexNetGAMStickData parentData = AlexNetGAMStickData.fromXml(generator.getDbUtil().readStimSpec(parentId).getSpec());
        sizeDiameter = parentData.sizeDiameter;
        location = parentData.location;

        //Generate Parent Stick
        AlexNetGAMatchStick parentMStick = new AlexNetGAMatchStick(parentData.light_position, parentData.stimColor, parentData.location, parentData.sizeDiameter, textureType);
        parentMStick.genMatchStickFromShapeSpec(parentData.stickSpec, new double[]{0,0,0});
        parentMStick.positionShape();


        //Generate Child Stick
        AlexNetGAMatchStick childMStick = new AlexNetGAMatchStick(light_position, color, location, sizeDiameter, textureType);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);

        return childMStick;
    }

}