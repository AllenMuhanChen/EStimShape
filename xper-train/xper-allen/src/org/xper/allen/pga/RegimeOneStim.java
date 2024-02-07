package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeOneStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;

    public RegimeOneStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords, double magnitude) {
        super(stimId, generator, parentId, size, coords);
        this.magnitude = magnitude;
    }


    @Override
    protected GrowingMatchStick createMStick() {
        //Generate MStick
        GrowingMatchStick parentMStick = new GrowingMatchStick();
        parentMStick.setProperties(calculateSize());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick(generator.getReceptiveField());
        childMStick.setProperties(calculateSize());
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }

}