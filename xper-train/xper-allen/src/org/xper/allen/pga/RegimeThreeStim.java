package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeThreeStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;

    public RegimeThreeStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords, double magnitude, String textureType) {
        super(stimId, generator, parentId, size, coords, textureType);
        this.magnitude = magnitude;
    }

    @Override
    protected GrowingMatchStick createMStick() {
        GrowingMatchStick parentMStick = new GrowingMatchStick(1.0/3.0);
        parentMStick.setProperties(calculateSize(), textureType);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick(generator.getReceptiveField());
        childMStick.setProperties(calculateSize(), textureType);
        childMStick.setStimColor(getRFColor());
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }
}