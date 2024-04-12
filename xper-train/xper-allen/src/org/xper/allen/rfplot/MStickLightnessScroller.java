package org.xper.allen.rfplot;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.HSLUtils;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import static org.xper.allen.rfplot.MStickHueScroller.updateValue;

public class MStickLightnessScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {

    private static final float LIGHTNESS_INCREMENT = 0.05f;  // Adjust this value based on your needs
    public MStickLightnessScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();


        float[] hsl = HSLUtils.rgbToHSL(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsl[2] = HSLUtils.adjustLightness(hsl[2], LIGHTNESS_INCREMENT);

        RGBColor newColor = HSLUtils.hslToRGB(hsl[0], hsl[1], hsl[2]);

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

        float[] hsl = HSLUtils.rgbToHSL(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsl[2] = HSLUtils.adjustLightness(hsl[2], -LIGHTNESS_INCREMENT);

        RGBColor newColor = HSLUtils.hslToRGB(hsl[0], hsl[1], hsl[2]);

        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }
}