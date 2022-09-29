package org.xper.rfplot;

import org.xper.Dependency;
import org.xper.rfplot.drawing.RFPlotDrawable;

public abstract class RFPlotScroller {

    RFPlotClient client;

    public RFPlotScroller(RFPlotClient client) {
        this.client = client;
    }

    public abstract void next(RFPlotDrawable drawable);
    public abstract void previous(RFPlotDrawable drawable);


}
