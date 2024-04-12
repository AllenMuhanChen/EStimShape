package org.xper.allen.pga;

import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeTwoStim extends GAStim<PruningMatchStick, PruningMatchStick.PruningMStickData>{
    public RegimeTwoStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords, String textureType) {
        super(stimId, generator, parentId, coords, textureType);
    }

    @Override
    protected PruningMatchStick createMStick() {
        PruningMatchStick parentMStick = new PruningMatchStick();
        parentMStick.setProperties(generator.getImageDimensionsDegrees(), textureType);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        PruningMatchStick childMStick = new PruningMatchStick(generator.getReceptiveField());
        childMStick.setProperties(generator.getImageDimensionsDegrees(), textureType);
        childMStick.setStimColor(getRFColor());
        childMStick.genPruningMatchStick(parentMStick, 0.75, 1);
        return childMStick;
    }
}