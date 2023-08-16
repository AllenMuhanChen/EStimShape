package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.drawing.Coordinates2D;

public class RegimeZeroStim extends GAStim<MorphedMatchStick, AllenMStickData> {

    private AllenMStickData mStickData;
    private long stimId;

    public RegimeZeroStim(Long stimId, FromDbGABlockGenerator generator, double size, Coordinates2D coords) {
        super(stimId, generator, 0L, size, coords);
    }

    @Override
    protected MorphedMatchStick createMStick() {
        MorphedMatchStick mStick = new MorphedMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees());
        mStick.genMatchStickRand();
        return mStick;
    }


}