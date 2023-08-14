package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeThreeStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;

    public RegimeThreeStim(FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords, double magnitude) {
        super(generator, parentId, size, coords);
        this.magnitude = magnitude;
    }

    @Override
    protected GrowingMatchStick createMStick() {
        GrowingMatchStick parentMStick = new GrowingMatchStick(1.0);
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }
}