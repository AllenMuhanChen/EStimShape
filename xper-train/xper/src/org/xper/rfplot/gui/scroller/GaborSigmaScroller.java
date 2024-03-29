package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class GaborSigmaScroller<T extends GaborSpec> extends RFPlotScroller<T>{

    public GaborSigmaScroller(Class<T> type) {
        this.type = type;
    }

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

    private void setNewSigma(ScrollerParams scrollerParams, double newSigma) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        currentGaborSpec.setSize(newSigma);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

    private double getCurrentSigma(ScrollerParams scrollerParams) {
        GaborSpec currentGaborSpec = getCurrentGaborSpec(scrollerParams);
        double currentSigma = currentGaborSpec.getDiameter();
        return currentSigma;
    }

    private GaborSpec getCurrentGaborSpec(ScrollerParams scrollerParams) {
        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        return currentGaborSpec;
    }


}