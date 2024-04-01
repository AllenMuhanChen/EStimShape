package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.png.HSLUtils;

public class LightnessScroller extends RFPlotScroller {

    private static final float LIGHTNESS_INCREMENT = 0.05f;  // Adjust this value based on your needs

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        return adjustLightness(scrollerParams, LIGHTNESS_INCREMENT);
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        return adjustLightness(scrollerParams, -LIGHTNESS_INCREMENT);
    }

    private ScrollerParams adjustLightness(ScrollerParams scrollerParams, float delta) {
        RFPlotXfmSpec xfmSpec = scrollerParams.getXfmSpec();
        RGBColor currentColor = xfmSpec.getColor();

        float[] hsl = HSLUtils.rgbToHSL(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsl[2] = HSLUtils.adjustLightness(hsl[2], delta);

        RGBColor newColor = HSLUtils.hslToRGB(hsl[0], hsl[1], hsl[2]);

        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, float[] hsl, RGBColor newColor) {
        scrollerParams.setNewValue("Lightness: " + hsl[2] + " RGB: " + newColor.toString());
    }
}