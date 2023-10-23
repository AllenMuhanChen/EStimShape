package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.RFPlotXfmSpec;

public class OrientationScroller extends RFPlotScroller{

    private final static float dr = (float) (10);

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        float currentRotation = xfmSpec.getRotation();
        float newRotation = currentRotation - dr;
        xfmSpec.setRotation(newRotation);
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        float currentRotation = xfmSpec.getRotation();
        float newRotation = currentRotation + dr;
        xfmSpec.setRotation(newRotation);
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }
}