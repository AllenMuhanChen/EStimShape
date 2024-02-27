package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class GaborHueScroller extends RFPlotScroller{

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        return null;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        return null;
    }

    private static GaborSpec getCurrentGaborSpec(ScrollerParams scrollerParams) {
        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
        GaborSpec currentGaborSpec = GaborSpec.fromXml(currentDrawable.getSpec());
        return currentGaborSpec;
    }
}