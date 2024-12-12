package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class LeafingStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;

    public LeafingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude, String textureType) {
        super(stimId, generator, parentId, textureType);
        this.magnitude = magnitude;
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseColor() {
        color = colorManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        sizeDiameterDegrees = sizeManager.readProperty(parentId);
    }

    @Override
    protected GrowingMatchStick createMStick() {
        GrowingMatchStick parentMStick = GrowingStim.initializeFromFile(generator.getReceptiveField(), textureType);
        parentMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees()), textureType);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick(generator.getReceptiveField(),
                parentMStick.getRfStrategy());

        sizeDiameterDegrees = sizeManager.readProperty(parentId);
        color = colorManager.readProperty(parentId);
        textureType = textureManager.readProperty(parentId);

        childMStick.setProperties(sizeDiameterDegrees, textureManager.readProperty(parentId));
        childMStick.setStimColor(color);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }
}