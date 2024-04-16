package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.RFMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class RegimeZeroStim extends GAStim<RFMatchStick, AllenMStickData> {

    public RegimeZeroStim(Long stimId, FromDbGABlockGenerator generator, Coordinates2D coords, String textureType, RGBColor color) {
        super(stimId, generator, 0L, coords, textureType, color);
    }

    @Override
    protected RFMatchStick createMStick() {
        RFMatchStick mStick = new RFMatchStick(generator.getReceptiveField());
        mStick.setProperties(calculateImageSize()/2, textureType);
        mStick.setStimColor(color);
        mStick.genMatchStickRand();
        return mStick;
    }

}