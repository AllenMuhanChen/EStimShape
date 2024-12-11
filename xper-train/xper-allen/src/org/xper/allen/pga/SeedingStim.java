package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.ColorUtils;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import java.util.Random;

public class SeedingStim extends GAStim<GAMatchStick, AllenMStickData> {
    private static final Random random = new Random();
    private static final double MAX_LUMINANCE_CHANGE = 0.25; // 25% maximum change

    public SeedingStim(Long stimId, FromDbGABlockGenerator generator, Coordinates2D coords, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, 0L, coords, textureType, color, rfStrategy);
    }

    @Override
    protected GAMatchStick createMStick() {
        GAMatchStick mStick = new GAMatchStick(
                generator.getReceptiveField(),
                RFStrategy.COMPLETELY_INSIDE, "SHADE");
        mStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees()), textureType);

        RGBColor mutatedColor = mutateLuminance(color);
        mStick.setStimColor(mutatedColor);

        mStick.genMatchStickRand();
        return mStick;
    }

    private RGBColor mutateLuminance(RGBColor originalColor) {
        // Get current luminance
        float currentLuminance = ColorUtils.getLuminance(originalColor);

        // Calculate random change between -25% and +25% of possible range
        double randomChange = (random.nextDouble() * 2 - 1) * MAX_LUMINANCE_CHANGE;

        // Apply change while keeping within valid range [0,1]
        double newLuminance = Math.min(1.0, Math.max(0.0, currentLuminance + randomChange));

        return ColorUtils.changeLuminance(originalColor, newLuminance);
    }
}