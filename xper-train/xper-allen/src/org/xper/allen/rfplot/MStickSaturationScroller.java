package org.xper.allen.rfplot;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.HSLUtils;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import static org.xper.allen.rfplot.MStickHueScroller.updateValue;

public class MStickSaturationScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T>{

    private static final float SATURATION_INCREMENT = 0.05f; // Adjust as necessary

    public MStickSaturationScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

        float[] hsl = HSLUtils.rgbToHSL(currentColor);

        // Adjust saturation
        hsl[1] += SATURATION_INCREMENT;
        if (hsl[1] > 1.0f) {
            hsl[1] = 1.0f;
        } else if (hsl[1] < 0.0f) {
            hsl[1] = 0.0f;
        }

        RGBColor newColor = HSLUtils.hslToRGB(hsl);
        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;

    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

        float[] hsl = HSLUtils.rgbToHSL(currentColor);

        // Adjust saturation
        hsl[1] -= SATURATION_INCREMENT;
        if (hsl[1] > 1.0f) {
            hsl[1] = 1.0f;
        } else if (hsl[1] < 0.0f) {
            hsl[1] = 0.0f;
        }

        RGBColor newColor = HSLUtils.hslToRGB(hsl);
        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }
}