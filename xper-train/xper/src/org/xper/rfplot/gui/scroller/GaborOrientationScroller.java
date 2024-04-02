package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.drawing.GaborSpec;

public class GaborOrientationScroller<T extends GaborSpec> extends RFPlotScroller<T>{

    public GaborOrientationScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        double currentOrientation = getCurrentOrientation(scrollerParams);
        double newOrientation = currentOrientation + 5;
        setNewOrientation(scrollerParams, newOrientation);
        updateValue(scrollerParams, newOrientation);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, double newOrientation) {
        scrollerParams.setNewValue(newOrientation + " degrees");
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        double currentOrientation = getCurrentOrientation(scrollerParams);
        double newOrientation = currentOrientation - 5;
        setNewOrientation(scrollerParams, newOrientation);
        updateValue(scrollerParams, newOrientation);
        return scrollerParams;
    }

    private double getCurrentOrientation(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        double currentOrientation = currentGaborSpec.getOrientation();
        return currentOrientation;
    }


//    private static GaborSpec getCurrentGaborSpec(ScrollerParams scrollerParams) {
//        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
//        GaborSpec currentGaborSpec = GaborSpec.fromXml(currentDrawable.getSpec());
//        return currentGaborSpec;
//    }

    private void setNewOrientation(ScrollerParams scrollerParams, double newOrientation) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        currentGaborSpec.setOrientation(newOrientation);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

}