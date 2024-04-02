package org.xper.allen.rfplot;

import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

public class MStickRotationScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {
    private int dim;
    private String[] dimNames = {"X Axis", "Y Axis", "Z Axis"};
    public MStickRotationScroller(Class<T> type, int dim) {
        this.type = type;
        this.dim = dim;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);

        double currentRotation = currentSpec.getRotation()[dim];
        double newRotation = currentRotation + 5;
        newSpec.getRotation()[dim] = newRotation;

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, newSpec);
        return scrollerParams;

    }

    private void updateValue(ScrollerParams scrollerParams, RFPlotMatchStick.RFPlotMatchStickSpec newSpec) {
        scrollerParams.setNewValue("Matchstick Rotation: " + newSpec.getRotation()[dim] + " degrees" + " around the " + dimNames[dim] + " axis");
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams)
    {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);

        double currentRotation = currentSpec.getRotation()[dim];
        double newRotation = currentRotation - 5;
        newSpec.getRotation()[dim] = newRotation;

        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, newSpec);
        return scrollerParams;
    }
}