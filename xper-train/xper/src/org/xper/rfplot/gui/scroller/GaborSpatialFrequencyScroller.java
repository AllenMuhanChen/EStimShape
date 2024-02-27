package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.XMLizable;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class GaborSpatialFrequencyScroller<T extends GaborSpec> extends RFPlotScroller<T>{
    public GaborSpatialFrequencyScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        double currentSpatialFrequency = getCurrentSpatialFrequency(scrollerParams);
        double newSpatialFrequency = currentSpatialFrequency + 0.20;
        setNewSpatialFrequency(scrollerParams, newSpatialFrequency);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        double currentSpatialFrequency = getCurrentSpatialFrequency(scrollerParams);
        double newSpatialFrequency = currentSpatialFrequency - 0.20;
        setNewSpatialFrequency(scrollerParams, newSpatialFrequency);
        return scrollerParams;
    }

    private double getCurrentSpatialFrequency(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        double currentSpatialFrequency = currentGaborSpec.getFrequency();
        return currentSpatialFrequency;
    }

    private void setNewSpatialFrequency(ScrollerParams scrollerParams, double newSpatialFrequency) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        currentGaborSpec.setFrequency(newSpatialFrequency);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }
}