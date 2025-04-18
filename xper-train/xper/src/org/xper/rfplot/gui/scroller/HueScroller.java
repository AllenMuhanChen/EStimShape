package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.png.HSLUtils;

import static org.xper.rfplot.drawing.png.HSLUtils.isPureWhite;

public class HueScroller extends RFPlotScroller {

    private static final float HUE_INCREMENT = 15f;  // Adjust this value based on your needs
    private boolean isWhite = false;
    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        float[] hsv = HSLUtils.rgbToHSV(currentColor);
        System.out.println("Current HSV: " + hsv[0] + ", " + hsv[1] + ", " + hsv[2]);
        if (Math.round(hsv[0]) == 360-HUE_INCREMENT) {

            System.out.println("Setting to White");
            hsv[0] = 0f;
            hsv[1] = 0f;
            isWhite = true;
        }
        else if (isWhite) {
            System.out.println("Setting White to First Hue");
            hsv[0] = 0f;
            hsv[1] = 1f;
            isWhite = false;
        } else {
            hsv[0] = HSLUtils.adjustHue(hsv[0], HUE_INCREMENT);
        }


        RGBColor newColor = HSLUtils.hsvToRGB(hsv);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        float[] hsv = HSLUtils.rgbToHSV(currentColor);
        if (Math.round(hsv[0]) == 0 && !isWhite) {
            System.out.println("Setting to White");
            hsv[0] = 360-HUE_INCREMENT; //doesn't matter what we set this, just NOT 0 or will retrigger
            hsv[1] = 0f;
            isWhite = true;
        }
        else if (isWhite) {
            hsv[0] = 360-HUE_INCREMENT;
            hsv[1] = 1f;
            isWhite = false;
        } else {
            hsv[0] = HSLUtils.adjustHue(hsv[0], -HUE_INCREMENT);
        }

        RGBColor newColor = HSLUtils.hsvToRGB(hsv);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
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

    private static void updateValue(ScrollerParams scrollerParams, float[] hsv, RGBColor newColor) {
        scrollerParams.setNewValue("Hue: " + hsv[0] + " RGB: " + newColor.toString());
    }

}