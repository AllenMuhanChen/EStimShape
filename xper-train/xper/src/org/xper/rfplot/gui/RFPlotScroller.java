package org.xper.rfplot.gui;

import org.xper.Dependency;
import org.xper.rfplot.RFPlotClient;
import org.xper.rfplot.drawing.RFPlotDrawable;

public abstract class RFPlotScroller {

    protected RFPlotClient client;

    public RFPlotScroller(RFPlotClient client) {
        this.client = client;
    }

    public abstract void next(RFPlotDrawable drawable);
    public abstract void previous(RFPlotDrawable drawable);


}
