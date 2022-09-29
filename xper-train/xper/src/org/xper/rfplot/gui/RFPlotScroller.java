package org.xper.rfplot.gui;

import org.xper.rfplot.RFPlotClient;

public abstract class RFPlotScroller {

    protected RFPlotClient client;

    public RFPlotScroller(RFPlotClient client) {
        this.client = client;
    }

    public abstract ScrollerParams next(ScrollerParams scrollerParams);
    public abstract ScrollerParams previous(ScrollerParams scrollerParams);


}
