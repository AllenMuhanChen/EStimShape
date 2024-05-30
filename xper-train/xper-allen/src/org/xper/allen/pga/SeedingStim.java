package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class SeedingStim extends GAStim<GAMatchStick, AllenMStickData> {

    public SeedingStim(Long stimId, FromDbGABlockGenerator generator, Coordinates2D coords, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, 0L, coords, textureType, color, rfStrategy);
    }

    @Override
    protected GAMatchStick createMStick() {
        GAMatchStick mStick = new GAMatchStick(
                generator.getReceptiveField(),
                RFStrategy.COMPLETELY_INSIDE, "SHADE");
        mStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource), textureType);
        mStick.setStimColor(color);
        mStick.genMatchStickRand();
        return mStick;
    }


}