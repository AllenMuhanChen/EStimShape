package org.xper.rfplot.gui.scroller;

import org.xper.rfplot.XMLizable;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;

/**
 *
 * @param <T>: Optional type parameter for allowing different types of GaborSpec
 *           to be used in the same scroller. To use it, subclass must
 *           specify Class<T> type parameter (i.e in constructor) when extending this class.
 *
 */
public abstract class RFPlotScroller<T extends XMLizable> {

    public Class<T> type;
    public abstract ScrollerParams next(ScrollerParams scrollerParams);
    public abstract ScrollerParams previous(ScrollerParams scrollerParams);

    protected T getCurrentSpec(ScrollerParams scrollerParams, Class specType) {
        RFPlotDrawable currentDrawable = scrollerParams.getRfPlotDrawable();
        T currentSpec;
        try {
            currentSpec = (T) specType.newInstance();
        } catch (InstantiationException e) {
            throw new RuntimeException(e);
        } catch (IllegalAccessException e) {
            throw new RuntimeException(e);
        }

        T spec = (T) currentSpec.getFromXml(currentDrawable.getSpec());
        return spec;
    }


}