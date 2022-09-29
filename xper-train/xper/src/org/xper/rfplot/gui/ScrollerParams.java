package org.xper.rfplot.gui;

import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

public class ScrollerParams {

    private RFPlotDrawable rfPlotDrawable;
    private RFPlotXfmSpec xfmSpec;

    public ScrollerParams(RFPlotDrawable rfPlotDrawable, RFPlotXfmSpec xfmSpec) {
        this.rfPlotDrawable = rfPlotDrawable;
        this.xfmSpec = xfmSpec;
    }

    public RFPlotDrawable getRfPlotDrawable() {
        return rfPlotDrawable;
    }

    public void setRfPlotDrawable(RFPlotDrawable rfPlotDrawable) {
        this.rfPlotDrawable = rfPlotDrawable;
    }

    public RFPlotXfmSpec getXfmSpec() {
        return xfmSpec;
    }

    public void setXfmSpec(RFPlotXfmSpec xfmSpec) {
        this.xfmSpec = xfmSpec;
    }
}
