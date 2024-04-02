package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;

public class GaborSpatialFrequencyScroller<T extends GaborSpec> extends RFPlotScroller<T>{
    public GaborSpatialFrequencyScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        double currentSpatialFrequency = getCurrentSpatialFrequency(scrollerParams);
        double newSpatialFrequency = currentSpatialFrequency + 0.1;
        setNewSpatialFrequency(scrollerParams, newSpatialFrequency);
        updateValue(scrollerParams, newSpatialFrequency);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, double newSpatialFrequency) {
        scrollerParams.setNewValue(newSpatialFrequency + " cycles/degree");
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        double currentSpatialFrequency = getCurrentSpatialFrequency(scrollerParams);
        double newSpatialFrequency = currentSpatialFrequency - 0.1;
        setNewSpatialFrequency(scrollerParams, newSpatialFrequency);
        updateValue(scrollerParams, newSpatialFrequency);
        return scrollerParams;
    }

    private double getCurrentSpatialFrequency(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        double currentSpatialFrequency = currentGaborSpec.getFrequency();
        return currentSpatialFrequency;
    }

    private void setNewSpatialFrequency(ScrollerParams scrollerParams, double newSpatialFrequency) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        currentGaborSpec.setFrequency(newSpatialFrequency);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }
}