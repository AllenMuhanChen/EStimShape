package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.gui.scroller.ScrollerParams;

public abstract class RFPlotScroller {

    public abstract ScrollerParams next(ScrollerParams scrollerParams);
    public abstract ScrollerParams previous(ScrollerParams scrollerParams);


}