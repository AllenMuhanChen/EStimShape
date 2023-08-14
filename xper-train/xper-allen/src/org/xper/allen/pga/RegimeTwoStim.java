package org.xper.allen.pga;

import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeTwoStim extends GAStim<PruningMatchStick, PruningMatchStick.PruningMStickData>{
    public RegimeTwoStim(FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords) {
        super(generator, parentId, size, coords);
    }

    @Override
    protected PruningMatchStick createMStick() {
        PruningMatchStick parentMStick = new PruningMatchStick();
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        PruningMatchStick childMStick = new PruningMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genPruningMatchStick(parentMStick, 0.75, 1);
        return childMStick;
    }
}