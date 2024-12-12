package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.drawing.ColorUtils;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.util.Random;

public class GrowingStim extends GAStim<GrowingMatchStick, AllenMStickData> {
    private final double magnitude;
    private static final Random random = new Random();
    private static final double MAX_LUMINANCE_CHANGE = 0.5;

    public GrowingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Coordinates2D coords, double magnitude, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, parentId, coords, textureType, color, rfStrategy);
        this.magnitude = magnitude;
    }


    @Override
    protected GrowingMatchStick createMStick() {
        //Generate MStick
        GrowingMatchStick parentMStick = initializeFromFile(generator.getReceptiveField(), textureType);
        parentMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees()), textureType);
        parentMStick.genMatchStickFromFile(
                generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        RGBColor parentColor = colorManager.readProperty(parentId);
        String parentTextureType = textureManager.readProperty(parentId);

        color = mutateLuminance(parentColor);

        GrowingMatchStick childMStick = new GrowingMatchStick(
                generator.getReceptiveField(),
                1/3.0,
                parentMStick.getRfStrategy(),
                parentTextureType);

        childMStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees()), parentTextureType);
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

    private RGBColor mutateLuminance(RGBColor originalColor) {
        // Get current luminance
        float currentLuminance = ColorUtils.getLuminance(originalColor);

        // Calculate random change between -25% and +25% of possible range
        double randomChange = (random.nextDouble()*magnitude * 2 - 1) * MAX_LUMINANCE_CHANGE;


        // Apply change while keeping within valid range [0,1]
        double newLuminance = Math.min(1.0, Math.max(0.0, currentLuminance + randomChange));

        return ColorUtils.changeLuminance(originalColor, newLuminance);
    }

}