package org.xper.rfplot.gui.scroller;

import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.RFPlotXfmSpec;

public class PngSizeScroller extends RFPlotScroller {

    public final static double SCALE_FACTOR = .1;

    public PngSizeScroller() {
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams){
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        Coordinates2D currentScale = xfmSpec.getScale();
        xfmSpec.setScale(new Coordinates2D(currentScale.getX()-SCALE_FACTOR, currentScale.getY()-SCALE_FACTOR));
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams){
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        Coordinates2D currentScale = xfmSpec.getScale();
        xfmSpec.setScale(new Coordinates2D(currentScale.getX()+SCALE_FACTOR, currentScale.getY()+SCALE_FACTOR));
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

}