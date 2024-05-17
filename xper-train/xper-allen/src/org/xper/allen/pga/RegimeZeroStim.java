package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class RegimeZeroStim extends GAStim<GAMatchStick, AllenMStickData> {

    public RegimeZeroStim(Long stimId, FromDbGABlockGenerator generator, Coordinates2D coords, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, 0L, coords, textureType, color, rfStrategy);
    }

    @Override
    protected GAMatchStick createMStick() {
        GAMatchStick mStick = new GAMatchStick(
                generator.getReceptiveField(),
                RFStrategy.COMPLETELY_INSIDE);
        mStick.setProperties(calculateMStickMaxSizeDegrees(), textureType);
        mStick.setStimColor(color);
        mStick.genMatchStickRand();
        return mStick;
    }


}