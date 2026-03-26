package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;

public class BaselineStim extends GAStim<GAMatchStick, AllenMStickData>{
    public BaselineStim(Long stimId, FromDbGABlockGenerator generator, Long parentId) {
        super(stimId, generator, parentId, "PARENT", true);
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
    protected GAMatchStick createMStick() {
        GAMatchStick childMStick = new GAMatchStick(position.getPosition());
        childMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        childMStick.setStimColor(color);
        childMStick.setMaxDiameterDegrees(generator.getImageDimensionsDegrees());
        childMStick.setRf(generator.getReceptiveField());
        childMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        position.setPosition(childMStick.getMassCenter());
        return childMStick;
    }
}
