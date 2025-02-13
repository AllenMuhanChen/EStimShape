package org.xper.rfplot.drawing.bar;

import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

public class BarOrientationScroller<T extends RFPlotBar.RFPlotBarSpec> extends RFPlotScroller<T> {
    private static final double ORIENTATION_INCREMENT = 5.0;

    public BarOrientationScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.orientation = (spec.orientation + ORIENTATION_INCREMENT) % 360;
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Orientation: %.1f degrees", spec.orientation));
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.orientation = (spec.orientation - ORIENTATION_INCREMENT + 360) % 360;
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Orientation: %.1f degrees", spec.orientation));
        return scrollerParams;
    }
}