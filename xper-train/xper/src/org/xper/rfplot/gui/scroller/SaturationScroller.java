package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.png.HSLUtils;

public class SaturationScroller extends RFPlotScroller {

    private static final float SATURATION_INCREMENT = 0.05f; // Adjust as necessary

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        float[] hsl = HSLUtils.rgbToHSL(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());

        // Adjust saturation
        hsl[1] += SATURATION_INCREMENT;
        if (hsl[1] > 1.0f) {
            hsl[1] = 1.0f;
        } else if (hsl[1] < 0.0f) {
            hsl[1] = 0.0f;
        }

        // Convert back to RGB and set the color
        RGBColor newColor = HSLUtils.hslToRGB(hsl[0], hsl[1], hsl[2]);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, float[] hsl, RGBColor newColor) {
        scrollerParams.setNewValue("Saturation: " + hsl[1] + " RGB: " + newColor.toString());
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        float[] hsl = HSLUtils.rgbToHSL(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());

        // Adjust saturation
        hsl[1] -= SATURATION_INCREMENT;
        if (hsl[1] > 1.0f) {
            hsl[1] = 1.0f;
        } else if (hsl[1] < 0.0f) {
            hsl[1] = 0.0f;
        }

        // Convert back to RGB and set the color
        RGBColor newColor = HSLUtils.hslToRGB(hsl[0], hsl[1], hsl[2]);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }


}