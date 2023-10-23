package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;

public class HueScroller extends RFPlotScroller {

    private static final float HUE_INCREMENT = 10f; // Adjust based on how fast you want the hue to change

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        System.out.println("Current color: " + currentColor.getRed() + ", " + currentColor.getGreen() + ", " + currentColor.getBlue());
        RGBColor newColor = getNextColor(currentColor);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();
        System.out.println("Current color: " + currentColor.getRed() + ", " + currentColor.getGreen() + ", " + currentColor.getBlue());
        RGBColor newColor = getPreviousColor(currentColor);
        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        return scrollerParams;
    }

    private RGBColor getNextColor(RGBColor currentColor) {
        float currentHue = getHueFromRGB(currentColor);
        currentHue += HUE_INCREMENT;
        if (currentHue >= 360.0f) {
            currentHue -= 360.0f;
        }
        return hueToRGB(currentHue);
    }

    private RGBColor getPreviousColor(RGBColor currentColor) {
        float currentHue = getHueFromRGB(currentColor);
        currentHue -= HUE_INCREMENT;
        if (currentHue < 0.0f) {
            currentHue += 360.0f;
        }
        return hueToRGB(currentHue);
    }

    private float getHueFromRGB(RGBColor rgbColor) {
        float r = rgbColor.getRed();
        float g = rgbColor.getGreen();
        float b = rgbColor.getBlue();

        float min = Math.min(Math.min(r, g), b);
        float max = Math.max(Math.max(r, g), b);

        float hue = 0.0f;
        if (max == r) {
            hue = (60.0f * ((g - b) / (max - min) + 0)) % 360;
        } else if (max == g) {
            hue = (60.0f * ((b - r) / (max - min) + 2)) % 360;
        } else if (max == b) {
            hue = (60.0f * ((r - g) / (max - min) + 4)) % 360;
        }

        if (hue < 0) {
            hue += 360.0f;
        }

        return hue;
    }

    private RGBColor hueToRGB(float hue) {
        int hi = (int) (hue / 60.0f) % 6;
        float f = (hue / 60.0f) - hi;
        float p = 0.0f; // Assuming full brightness and saturation
        float q = 1.0f - f;
        float t = f;

        switch (hi) {
            case 0:
                return new RGBColor(1.0f, t, p);
            case 1:
                return new RGBColor(q, 1.0f, p);
            case 2:
                return new RGBColor(p, 1.0f, t);
            case 3:
                return new RGBColor(p, q, 1.0f);
            case 4:
                return new RGBColor(t, p, 1.0f);
            case 5:
                return new RGBColor(1.0f, p, q);
            default:
                return new RGBColor(1.0f, 1.0f, 1.0f); // default to white for any invalid inputs
        }
    }
}