package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class RegimeOneStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;

    public RegimeOneStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Coordinates2D coords, double magnitude, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, parentId, coords, textureType, color, rfStrategy);
        this.magnitude = magnitude;

    }


    @Override
    protected GrowingMatchStick createMStick() {
        //Generate MStick
        GrowingMatchStick parentMStick = new GrowingMatchStick();
        parentMStick.setProperties(calculateMStickMaxSizeDegrees(), textureType);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick(generator.getReceptiveField(), rfStrategy);
        childMStick.setProperties(calculateMStickMaxSizeDegrees(), textureType);
        childMStick.setStimColor(color);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }

}