package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.IsochromaticGaborSpec;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.png.HSLUtils;

import static org.xper.rfplot.drawing.png.HSLUtils.isPureWhite;


public class GaborHueScroller<T extends IsochromaticGaborSpec> extends RFPlotScroller<T>{
    private static final float HUE_INCREMENT = 0.05f;

    public GaborHueScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams)
    {
        RGBColor currentColor = getCurrentColor(scrollerParams);
        float[] hsl = HSLUtils.rgbToHSL(currentColor);

        if (isPureWhite(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
            hsl[2] = 0.5f; // Reduce lightness to allow color to show
        } else if (isGrayscale(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
        } else {
            hsl[0] = HSLUtils.adjustHue(hsl[0], HUE_INCREMENT);
        }

        RGBColor newColor = HSLUtils.hslToRGB(hsl);
        setNewColor(scrollerParams, newColor);
        return scrollerParams;
    }


    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RGBColor currentColor = getCurrentColor(scrollerParams);
        float[] hsl = HSLUtils.rgbToHSL(currentColor);

        if (isPureWhite(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], -HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
            hsl[2] = 0.5f; // Reduce lightness to allow color to show
        } else if (isGrayscale(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], -HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
        } else {
            hsl[0] = HSLUtils.adjustHue(hsl[0], -HUE_INCREMENT);
        }

        RGBColor newColor = HSLUtils.hslToRGB(hsl);
        setNewColor(scrollerParams, newColor);
        return scrollerParams;
    }


    private void setNewColor(ScrollerParams scrollerParams, RGBColor newColor) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        currentGaborSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

    private RGBColor getCurrentColor(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams, type);
        RGBColor currentColor = currentGaborSpec.getColor();
        return currentColor;
    }

    private boolean isGrayscale(RGBColor color) {
        return color.getRed() == color.getGreen() && color.getGreen() == color.getBlue();
    }


}