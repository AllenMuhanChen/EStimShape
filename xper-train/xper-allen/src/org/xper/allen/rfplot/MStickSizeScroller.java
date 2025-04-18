package org.xper.allen.rfplot;

import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

public class MStickSizeScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {

    public static final double STEP_SIZE = 1.0;

    public MStickSizeScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        double currentSize = currentSpec.getSizeDiameterDegrees();
        newSpec.setSizeDiameterDegrees(currentSize + STEP_SIZE);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Matchstick Size: " + newSpec.getSizeDiameterDegrees() + " degrees");
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        double currentSize = currentSpec.getSizeDiameterDegrees();
        double newSize = currentSize - STEP_SIZE;
        if (newSize < 0) {
            newSize = 0;
        }
        newSpec.setSizeDiameterDegrees(newSize);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        scrollerParams.setNewValue("Matchstick Size: " + newSpec.getSizeDiameterDegrees() + " degrees");
        return scrollerParams;
    }
}