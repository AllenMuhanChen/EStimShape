package org.xper.rfplot.gui;

import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.RFPlotStimSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

public class PngSizeScroller extends RFPlotScroller{

    public final static double SCALE_FACTOR = 1;

    public PngSizeScroller(RFPlotClient client) {
        super(client);
    }

    @Override
    public void next(RFPlotDrawable pngDrawable) {
        PngSpec pngSpec = PngSpec.fromXml(pngDrawable.getSpec());
        ImageDimensions currentDimensions = pngSpec.getDimensions();
        ImageDimensions nextDimensions = new ImageDimensions(currentDimensions.getWidth()-SCALE_FACTOR, currentDimensions.getHeight()-SCALE_FACTOR);
        pngSpec.setDimensions(nextDimensions);
        pngDrawable.setSpec(pngSpec.toXml());
        String nextStimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(pngDrawable);
        client.changeRFPlotStim(nextStimSpec);
    }

    @Override
    public void previous(RFPlotDrawable pngDrawable) {
        PngSpec pngSpec = PngSpec.fromXml(pngDrawable.getSpec());
        ImageDimensions currentDimensions = pngSpec.getDimensions();
        ImageDimensions nextDimensions = new ImageDimensions(currentDimensions.getWidth()+SCALE_FACTOR, currentDimensions.getHeight()+SCALE_FACTOR);
        pngSpec.setDimensions(nextDimensions);
        pngDrawable.setSpec(pngSpec.toXml());
        String nextStimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(pngDrawable);
        client.changeRFPlotStim(nextStimSpec);
    }
}
