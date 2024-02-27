package org.xper.rfplot.gui.scroller;

import org.xper.Dependency;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.IsochromaticGaborSpec;

import java.util.Arrays;

public class GaborIsochromaticScroller <T extends IsochromaticGaborSpec> extends RFPlotScroller<T>{

    public GaborIsochromaticScroller(Class<T> type) {
        this.type = type;
    }

    RGBColor[] colors = {
            new RGBColor(1, 1, 1),
            new RGBColor(1, 0, 0),
            new RGBColor(0, 1, 0),
            new RGBColor(0, 1, 1),
            new RGBColor(1, 1, 0)};

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RGBColor currentColor = getCurrentColor(scrollerParams);
        System.out.println("currentColor: " + currentColor.toString());
        int index = Arrays.asList(colors).indexOf(currentColor);
        RGBColor newColor;
        if (index == -1) {
            newColor = colors[0];
        } else {
            newColor = colors[(index + 1) % colors.length];
        }
        setNewColor(scrollerParams, newColor);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RGBColor currentColor = getCurrentColor(scrollerParams);
        int index = Arrays.asList(colors).indexOf(currentColor);
        RGBColor newColor;
        if (index == -1) {
            newColor = colors[0];
        } else {
            newColor = colors[(index - 1 + colors.length) % colors.length];
        }
        setNewColor(scrollerParams, newColor);
        return scrollerParams;
    }

    private RGBColor getCurrentColor(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        RGBColor currentColor = currentGaborSpec.getColor();
        return currentColor;
    }

    private void setNewColor(ScrollerParams scrollerParams, RGBColor newColor) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        currentGaborSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

    public RGBColor[] getColors() {
        return colors;
    }

    public void setColors(RGBColor[] colors) {
        this.colors = colors;
    }
}