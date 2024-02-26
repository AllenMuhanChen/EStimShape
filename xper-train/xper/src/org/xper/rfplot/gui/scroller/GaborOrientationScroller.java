package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class GaborOrientationScroller extends RFPlotScroller{

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        double currentOrientation = getCurrentOrientation(scrollerParams);
        double newOrientation = currentOrientation + 10;
        setNewOrientation(scrollerParams, newOrientation);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        double currentOrientation = getCurrentOrientation(scrollerParams);
        double newOrientation = currentOrientation - 10;
        setNewOrientation(scrollerParams, newOrientation);
        return scrollerParams;
    }

    private double getCurrentOrientation(ScrollerParams scrollerParams) {
        GaborSpec currentGaborSpec = getCurrentGaborSpec(scrollerParams);
        double currentOrientation = currentGaborSpec.getOrientation();
        return currentOrientation;
    }


    private static GaborSpec getCurrentGaborSpec(ScrollerParams scrollerParams) {
        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
        GaborSpec currentGaborSpec = GaborSpec.fromXml(currentDrawable.getSpec());
        return currentGaborSpec;
    }

    private static void setNewOrientation(ScrollerParams scrollerParams, double newOrientation) {
        GaborSpec currentGaborSpec = getCurrentGaborSpec(scrollerParams);
        currentGaborSpec.setOrientation(newOrientation);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

}