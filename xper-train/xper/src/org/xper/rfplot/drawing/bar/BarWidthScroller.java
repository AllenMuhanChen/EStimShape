package org.xper.rfplot.drawing.bar;

import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

public class BarWidthScroller<T extends RFPlotBar.RFPlotBarSpec> extends RFPlotScroller<T> {
    private static final double WIDTH_INCREMENT = 0.25;

    public BarWidthScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.width += WIDTH_INCREMENT;
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Width: %.1f degrees", spec.width));
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.width = Math.max(0.1, spec.width - WIDTH_INCREMENT);
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Width: %.1f degrees", spec.width));
        return scrollerParams;
    }
}