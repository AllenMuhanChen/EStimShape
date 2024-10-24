package org.xper.allen.pga.alexnet;

import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class GrowingStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData>{

    public GrowingStim(FromDbAlexNetGABlockGenerator generator, Long parentId, Long stimId, String textureType, RGBColor color, Coordinates2D location, float[] light_position, double sizeDiameter, double magnitude) {
        super(generator, parentId, stimId, textureType, color, location, light_position, sizeDiameter, magnitude);
    }

    @Override
    public AlexNetGAMatchStick createMStick() {
        //Read the parent properties, including position, size, etc.
        AlexNetGAMStickData parentData = AlexNetGAMStickData.fromXml(generator.getDbUtil().readStimSpec(parentId).getSpec());

        //TODO: This correction is because when you load from a file / spec, the size is multiplied again by scale.
        //TODO: we either need to fix the genFromShapeSpec to undo scaling, or finalize what we're doing in smoothize

//        double parentSizeDiameter = parentData.sizeDiameter;
//        double newSizeDiameter = sizeDiameter / parentSizeDiameter;
//        this.sizeDiameter = newSizeDiameter;


        //Generate Parent Stick
        AlexNetGAMatchStick parentMStick = new AlexNetGAMatchStick(parentData.light_position, parentData.stimColor, parentData.location, parentData.sizeDiameter, textureType);
        parentMStick.genMatchStickFromShapeSpec(parentData.mStickSpec, new double[]{0,0,0});


        //Generate Child Stick
        AlexNetGAMatchStick childMStick = new AlexNetGAMatchStick(light_position, color, location, sizeDiameter, textureType);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);


        return childMStick;
    }
}