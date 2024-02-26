package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class GaborSigmaScroller extends RFPlotScroller{
    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        double currentSigma = getCurrentSigma(scrollerParams);
        double newSigma = currentSigma + 1;
        System.out.println("newSigma: " + newSigma);
        setNewSigma(scrollerParams, newSigma);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        double currentSigma = getCurrentSigma(scrollerParams);
        double newSigma = currentSigma - 1;
        setNewSigma(scrollerParams, newSigma);
        return scrollerParams;
    }

    private static void setNewSigma(ScrollerParams scrollerParams, double newSigma) {
        GaborSpec currentGaborSpec = getCurrentGaborSpec(scrollerParams);
        currentGaborSpec.setSize(newSigma);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

    private double getCurrentSigma(ScrollerParams scrollerParams) {
        GaborSpec currentGaborSpec = getCurrentGaborSpec(scrollerParams);
        double currentSigma = currentGaborSpec.getSize();
        return currentSigma;
    }

    private static GaborSpec getCurrentGaborSpec(ScrollerParams scrollerParams) {
        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
        GaborSpec currentGaborSpec = GaborSpec.fromXml(currentDrawable.getSpec());
        return currentGaborSpec;
    }


}