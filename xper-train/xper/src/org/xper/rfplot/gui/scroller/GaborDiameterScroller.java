package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class GaborDiameterScroller<T extends GaborSpec> extends RFPlotScroller<T>{

    public GaborDiameterScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        double currentSigma = getCurrentDiameter(scrollerParams);
        double newDiameter = currentSigma + 1;
        setNewDiameter(scrollerParams, newDiameter);
        updateValue(scrollerParams, newDiameter);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, double newDiameter) {
        scrollerParams.setNewValue(newDiameter + " degrees");
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        double currentSigma = getCurrentDiameter(scrollerParams);
        double newDiameter = currentSigma - 1;
        setNewDiameter(scrollerParams, newDiameter);
        updateValue(scrollerParams, newDiameter);
        return scrollerParams;
    }

    private void setNewDiameter(ScrollerParams scrollerParams, double newDiameter) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        currentGaborSpec.setSize(newDiameter);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

    private double getCurrentDiameter(ScrollerParams scrollerParams) {
        GaborSpec currentGaborSpec = getCurrentGaborSpec(scrollerParams);
        double currentSigma = currentGaborSpec.getDiameter();
        return currentSigma;
    }

    private GaborSpec getCurrentGaborSpec(ScrollerParams scrollerParams) {
        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        return currentGaborSpec;
    }


}