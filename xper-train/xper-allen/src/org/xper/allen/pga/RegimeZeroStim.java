package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public class RegimeZeroStim extends GAStim<MorphedMatchStick, AllenMStickData> {

    private AllenMStickData mStickData;
    private long stimId;

    public RegimeZeroStim(FromDbGABlockGenerator generator, double size, Coordinates2D coords) {
        super(generator, 0L, size, coords);
    }

    @Override
    protected MorphedMatchStick createMStick() {
        MorphedMatchStick mStick = new MorphedMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees());
        mStick.genMatchStickRand();
        return mStick;
    }


}