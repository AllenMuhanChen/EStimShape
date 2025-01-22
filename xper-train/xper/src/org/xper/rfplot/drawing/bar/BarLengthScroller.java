package org.xper.rfplot.drawing.bar;

import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

public class BarLengthScroller<T extends RFPlotBar.RFPlotBarSpec> extends RFPlotScroller<T> {
    private static final double LENGTH_INCREMENT = 0.5;

    public BarLengthScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.length += LENGTH_INCREMENT;
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Length: %.1f degrees", spec.length));
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotBar.RFPlotBarSpec spec = getCurrentSpec(scrollerParams);
        spec.length = Math.max(0.1, spec.length - LENGTH_INCREMENT);
        scrollerParams.getRfPlotDrawable().setSpec(spec.toXml());
        scrollerParams.setNewValue(String.format("Length: %.1f degrees", spec.length));
        return scrollerParams;
    }
}