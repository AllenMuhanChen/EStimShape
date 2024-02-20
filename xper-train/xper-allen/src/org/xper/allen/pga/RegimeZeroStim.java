package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.RFMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeZeroStim extends GAStim<RFMatchStick, AllenMStickData> {

    private AllenMStickData mStickData;
    private long stimId;

    public RegimeZeroStim(Long stimId, FromDbGABlockGenerator generator, double size, Coordinates2D coords, String textureType) {
        super(stimId, generator, 0L, size, coords, textureType);
    }

    @Override
    protected RFMatchStick createMStick() {
        RFMatchStick mStick = new RFMatchStick(generator.getReceptiveField());
        mStick.setProperties(calculateSize(), textureType);
        mStick.setStimColor(getRFColor());
        mStick.genMatchStickRand();
        return mStick;
    }

}