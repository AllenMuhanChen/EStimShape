package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.png.HSLUtils;

import static org.xper.rfplot.drawing.png.HSLUtils.isPureWhite;

public class HueScroller extends RFPlotScroller {

    private static final float HUE_INCREMENT = 0.05f;  // Adjust this value based on your needs

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
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
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        return adjustHue(scrollerParams, -HUE_INCREMENT);
    }

    private ScrollerParams adjustHue(ScrollerParams scrollerParams, float delta) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();

        float[] hsl = HSLUtils.rgbToHSL(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsl[0] = HSLUtils.adjustHue(hsl[0], delta);

        RGBColor newColor = HSLUtils.hslToRGB(hsl[0], hsl[1], hsl[2]);

        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        scrollerParams.setNewValue(newColor.toString());
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }

    private boolean isGrayscale(RGBColor color) {
        return color.getRed() == color.getGreen() && color.getGreen() == color.getBlue();
    }

    private static void updateValue(ScrollerParams scrollerParams, float[] hsl, RGBColor newColor) {
        scrollerParams.setNewValue("Hue: " + hsl[0] + " RGB: " + newColor.toString());
    }

}