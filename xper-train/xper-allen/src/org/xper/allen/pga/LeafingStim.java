package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class LeafingStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;

    public LeafingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Coordinates2D coords, double magnitude, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, parentId, coords, textureType, color, rfStrategy);
        this.magnitude = magnitude;
    }

    @Override
    protected GrowingMatchStick createMStick() {
        GrowingMatchStick parentMStick = GrowingStim.initializeFromFile(generator.getReceptiveField(), textureType);
        parentMStick.setProperties(RFUtils.calculateMStickMaxSizeDegrees(rfStrategy, generator.rfSource), textureType);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick(generator.getReceptiveField(),
                parentMStick.getRfStrategy());
        childMStick.setProperties(RFUtils.calculateMStickMaxSizeDegrees(rfStrategy, generator.rfSource), textureType);
        childMStick.setStimColor(color);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }
}