package org.xper.rfplot.gui;

import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.RFPlotXfmSpec;

public class PngSizeScroller extends RFPlotScroller{

    public final static double SCALE_FACTOR = .1;

    public PngSizeScroller(RFPlotClient client) {
        super(client);
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams){
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        Coordinates2D currentScale = xfmSpec.getScale();
        xfmSpec.setScale(new Coordinates2D(currentScale.getX()-SCALE_FACTOR, currentScale.getY()-SCALE_FACTOR));
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams){
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        Coordinates2D currentScale = xfmSpec.getScale();
        xfmSpec.setScale(new Coordinates2D(currentScale.getX()+SCALE_FACTOR, currentScale.getY()+SCALE_FACTOR));
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

//    @Override
//    public void next(ScrollerParams scrollerInput) {
//        PngSpec pngSpec = PngSpec.fromXml(scrollerInput.getRfPlotDrawable().getSpec());
//        ImageDimensions currentDimensions = pngSpec.getDimensions();
//        ImageDimensions nextDimensions = new ImageDimensions(currentDimensions.getWidth()-SCALE_FACTOR, currentDimensions.getHeight()-SCALE_FACTOR);
//        pngSpec.setDimensions(nextDimensions);
//        scrollerInput.getRfPlotDrawable().setSpec(pngSpec.toXml());
//        String nextStimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(scrollerInput.getRfPlotDrawable());
//        client.changeRFPlotStim(nextStimSpec);
//    }

//    @Override
//    public void previous(ScrollerParams scrollerInput) {
//        PngSpec pngSpec = PngSpec.fromXml(scrollerInput.getRfPlotDrawable().getSpec());
//        ImageDimensions currentDimensions = pngSpec.getDimensions();
//        ImageDimensions nextDimensions = new ImageDimensions(currentDimensions.getWidth()+SCALE_FACTOR, currentDimensions.getHeight()+SCALE_FACTOR);
//        pngSpec.setDimensions(nextDimensions);
//        scrollerInput.getRfPlotDrawable().setSpec(pngSpec.toXml());
//        String nextStimSpec = RFPlotStimSpec.getStimSpecFromRFPlotDrawable(scrollerInput.getRfPlotDrawable());
//        client.changeRFPlotStim(nextStimSpec);
//    }
}
