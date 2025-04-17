package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;

import java.util.Random;

public class GrowingStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;
    private static final Random random = new Random();

    public GrowingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude, String textureType) {
        super(stimId, generator, parentId, textureType, true);
        this.magnitude = magnitude;
    }


    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        double maxSizeDiameterDegrees = RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees());
        double minSizeDiameterDegrees = maxSizeDiameterDegrees / 2;
        double parentSizeDiameterDegrees = sizeManager.readProperty(parentId);
        double maxSizeMutation = (maxSizeDiameterDegrees - minSizeDiameterDegrees);
        double randomChange = (random.nextDouble() * magnitude * 2 - 1) * maxSizeMutation;
        sizeDiameterDegrees = Math.min(maxSizeDiameterDegrees, Math.max(minSizeDiameterDegrees, parentSizeDiameterDegrees + randomChange));
    }


    private void mutateContrast() {
        boolean isMutate = Math.random() < magnitude;
        if (isMutate){
            if (contrast == 0.4){
                contrast = 1.0;
            } else if (contrast == 1.0){
                contrast = 0.4;
            } else {
                throw new IllegalArgumentException("Invalid contrast value: " + contrast + ". Expected 0.4 or 1.0.");
            }
        }
    }

    @Override
    protected GrowingMatchStick createMStick() {
        //Generate MStick
        GrowingMatchStick parentMStick = initializeFromFile(generator.getReceptiveField(), textureType);
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(
                generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        rfStrategy = parentMStick.getRfStrategy();

        GrowingMatchStick childMStick = new GrowingMatchStick(
                generator.getReceptiveField(),
                1/3.0,
                rfStrategy,
                textureType);

        childMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        childMStick.setStimColor(color);
        childMStick.genGrowingMatchStick(parentMStick, magnitude);
        return childMStick;
    }

    public static GrowingMatchStick initializeFromFile(ReceptiveField receptiveField, String textureType) {
        return new GrowingMatchStick(receptiveField,
                1 / 3.0,
                null,
                textureType);
    }


}