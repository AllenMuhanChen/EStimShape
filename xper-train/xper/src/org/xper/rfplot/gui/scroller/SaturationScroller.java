package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.png.HSVUtils;

public class SaturationScroller extends RFPlotScroller {

    private static final float SATURATION_INCREMENT = 0.05f; // Adjust as necessary

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        float[] hsv = HSVUtils.rgbToHSV(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());

        // Adjust saturation
        hsv[1] += SATURATION_INCREMENT;
        if (hsv[1] > 1.0f) {
            hsv[1] = 1.0f;
        } else if (hsv[1] < 0.0f) {
            hsv[1] = 0.0f;
        }

        // Convert back to RGB and set the color
        RGBColor newColor = HSVUtils.hsvToRGB(hsv[0], hsv[1], hsv[2]);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, float[] hsv, RGBColor newColor) {
        scrollerParams.setNewValue("Saturation: " + hsv[1] + " RGB: " + newColor.toString());
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        float[] hsv = HSVUtils.rgbToHSV(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());

        // Adjust saturation
        hsv[1] -= SATURATION_INCREMENT;
        if (hsv[1] > 1.0f) {
            hsv[1] = 1.0f;
        } else if (hsv[1] < 0.0f) {
            hsv[1] = 0.0f;
        }

        // Convert back to RGB and set the color
        RGBColor newColor = HSVUtils.hsvToRGB(hsv[0], hsv[1], hsv[2]);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }


}