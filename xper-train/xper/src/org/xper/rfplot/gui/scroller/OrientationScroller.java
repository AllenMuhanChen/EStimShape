package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.RFPlotXfmSpec;

public class OrientationScroller extends RFPlotScroller{

    private final static float dr = (float) (5);

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        float currentRotation = xfmSpec.getRotation();
        float newRotation = currentRotation - dr;
        xfmSpec.setRotation(newRotation);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, newRotation);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, float newRotation) {
        scrollerParams.setNewValue("Rotation: " + newRotation + " degrees");
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        float currentRotation = xfmSpec.getRotation();
        float newRotation = currentRotation + dr;
        xfmSpec.setRotation(newRotation);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, newRotation);
        return scrollerParams;
    }
}