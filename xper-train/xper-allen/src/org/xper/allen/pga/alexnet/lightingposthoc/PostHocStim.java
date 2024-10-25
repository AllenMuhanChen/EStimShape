package org.xper.allen.pga.alexnet.lightingposthoc;

import org.xper.allen.pga.alexnet.AlexNetGAMStickData;
import org.xper.allen.pga.alexnet.AlexNetGAMatchStick;
import org.xper.allen.pga.alexnet.AlexNetGAStim;
import org.xper.allen.pga.alexnet.FromDbAlexNetGABlockGenerator;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class PostHocStim extends AlexNetGAStim<AlexNetGAMatchStick, AlexNetGAMStickData> {
    public PostHocStim(LightingPostHocGenerator generator, StimInstruction instructions){
        super(generator, instructions.getParentId(), instructions.getStimId(), instructions.getTextureType(),null, null, instructions.getLightPosition(), 0, 0, instructions.getContrast());
    }

    @Override
    protected AlexNetGAMatchStick createMStick() {
        //Read the parent properties, including position, size, etc.
        AlexNetGAMStickData parentData = AlexNetGAMStickData.fromXml(generator.getDbUtil().readStimSpec(parentId).getSpec());
        sizeDiameter = parentData.sizeDiameter;
        location = parentData.location;
        color = parentData.stimColor;;

        //Generate Stick
        AlexNetGAMatchStick newMStick = new AlexNetGAMatchStick(light_position, color, location, sizeDiameter, textureType, contrast);
        newMStick.genMatchStickFromShapeSpec(parentData.stickSpec, new double[]{0,0,0});
        newMStick.positionShape();

        return newMStick;
    }
}