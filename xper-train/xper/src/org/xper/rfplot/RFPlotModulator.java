package org.xper.rfplot;

import org.xper.rfplot.drawing.RFPlotDrawable;

public interface RFPlotModulator {
    public RFPlotStimSpec next(RFPlotStimSpec stimSpec);
    public RFPlotStimSpec previous(RFPlotStimSpec stimSpec);

    public void nextMode();

    public void previousMode();

}
