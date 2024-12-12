package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.ColorUtils;
import org.xper.drawing.RGBColor;

import java.util.Random;

public class GrowingStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;
    private static final Random random = new Random();
    private static final double MAX_LUMINANCE_CHANGE = 0.5;

    public GrowingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude, String textureType, RGBColor color) {
        super(stimId, generator, parentId, textureType, color);
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

    @Override
    protected void chooseColor() {
        RGBColor originalColor = colorManager.readProperty(parentId);
        // Get current luminance
        float currentLuminance = ColorUtils.getLuminance(originalColor);

        // Calculate random change between -25% and +25% of possible range
        double randomChange = (random.nextDouble()*magnitude * 2 - 1) * MAX_LUMINANCE_CHANGE;


        // Apply change while keeping within valid range [0,1]
        double newLuminance = Math.min(1.0, Math.max(0.0, currentLuminance + randomChange));

        color = ColorUtils.changeLuminance(originalColor, newLuminance);
    }

    @Override
    protected GrowingMatchStick createMStick() {
        //Generate MStick
        GrowingMatchStick parentMStick = initializeFromFile(generator.getReceptiveField(), textureType);
        parentMStick.setProperties(sizeDiameterDegrees, textureType);
        parentMStick.genMatchStickFromFile(
                generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        rfStrategy = parentMStick.getRfStrategy();

        GrowingMatchStick childMStick = new GrowingMatchStick(
                generator.getReceptiveField(),
                1/3.0,
                rfStrategy,
                textureType);

        childMStick.setProperties(sizeDiameterDegrees, textureType);
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