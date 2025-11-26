package org.xper.allen.pga;

import org.xper.allen.drawing.composition.morph.PruningMatchStick;

public class PruningStim extends GAStim<PruningMatchStick, PruningMatchStick.PruningMStickData>{
    public PruningStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, String textureType) {
        super(stimId, generator, parentId, textureType, true);
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        sizeDiameterDegrees = sizeManager.readProperty(parentId);
    }

    @Override
    protected PruningMatchStick createMStick() {
        PruningMatchStick parentMStick = new PruningMatchStick(null);
        parentMStick.setProperties(sizeDiameterDegrees, textureType, 1.0);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        PruningMatchStick childMStick = new PruningMatchStick(generator.getReceptiveField(), rfStrategy, null);
        childMStick.setProperties(sizeDiameterDegrees, textureType, contrast);
        childMStick.setStimColor(color);

        childMStick.genPruningMatchStick(parentMStick, 0.75, PruningMatchStick.chooseRandomComponentsToPreserve(1, parentMStick), null);
        return childMStick;
    }
}