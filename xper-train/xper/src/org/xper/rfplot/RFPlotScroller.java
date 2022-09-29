package org.xper.rfplot;

import org.xper.rfplot.drawing.RFPlotDrawable;

public interface RFPlotScroller {
    public void next(RFPlotDrawable drawable);
    public void previous(RFPlotDrawable drawable);
}
