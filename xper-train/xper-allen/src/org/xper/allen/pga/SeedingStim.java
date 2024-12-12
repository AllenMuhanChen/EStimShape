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

    public SeedingStim(Long stimId, FromDbGABlockGenerator generator, String textureType, RGBColor color) {
        super(stimId, generator, 0L, textureType, color, RFStrategy.COMPLETELY_INSIDE);
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = RFStrategy.COMPLETELY_INSIDE;
    }

    @Override
    protected void chooseSize() {
        double maxSizeDiameterDegrees = RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees());
        double minSizeDiameterDegrees = maxSizeDiameterDegrees / 2;

        sizeDiameterDegrees = minSizeDiameterDegrees + random.nextDouble() * (maxSizeDiameterDegrees - minSizeDiameterDegrees);
    }

    @Override
    protected void chooseColor() {
        RGBColor originalColor = color;
        // Get current luminance
        float currentLuminance = ColorUtils.getLuminance(originalColor);

        // Calculate random change between -25% and +25% of possible range
        double randomChange = (random.nextDouble() * 2 - 1) * MAX_LUMINANCE_CHANGE;

        // Apply change while keeping within valid range [0,1]
        double newLuminance = Math.min(1.0, Math.max(0.0, currentLuminance + randomChange));

        color = ColorUtils.changeLuminance(originalColor, newLuminance);
    }

    @Override
    protected GAMatchStick createMStick() {
        GAMatchStick mStick = new GAMatchStick(
                generator.getReceptiveField(),
                rfStrategy);


        mStick.setProperties(sizeDiameterDegrees, textureType);
        mStick.setStimColor(color);

        mStick.genMatchStickRand();

        return mStick;
    }
}