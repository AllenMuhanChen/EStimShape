package org.xper.rfplot.drawing.bar;

import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

public class BarSizeScroller<T extends RFPlotBar.RFPlotBarSpec> extends RFPlotScroller<T> {
    private static final double SIZE_FACTOR = 1.1;

    public BarSizeScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.length *= SIZE_FACTOR;
        spec.width *= SIZE_FACTOR;
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Length: %.1f Width: %.1f", spec.length, spec.width));
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.length /= SIZE_FACTOR;
        spec.width /= SIZE_FACTOR;
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Length: %.1f Width: %.1f", spec.length, spec.width));
        return scrollerParams;
    }
}