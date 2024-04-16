package org.xper.allen.pga;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.RFMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

public class CatchStim implements Stim
{

    private final FromDbGABlockGenerator generator;
    private final Long stimId;

    public CatchStim(Long stimId, FromDbGABlockGenerator generator) {
        this.generator = generator;
        this.stimId = stimId;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        PngSpec pngSpec = new PngSpec();
        pngSpec.setPath("catch");
        pngSpec.setDimensions(new ImageDimensions(0, 0));
        pngSpec.setxCenter(0);
        pngSpec.setyCenter(0);

        generator.getDbUtil().writeStimSpec(stimId, pngSpec.toXml());

    }


    @Override
    public Long getStimId() {
        return stimId;
    }
}