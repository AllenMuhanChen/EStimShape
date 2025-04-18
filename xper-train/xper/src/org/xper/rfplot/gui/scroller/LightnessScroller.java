package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.RFPlotXfmSpec;
import org.xper.rfplot.drawing.png.HSVUtils;

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

        float[] hsv = HSVUtils.rgbToHSV(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsv[2] = HSVUtils.adjustValue(hsv[2], delta);

        RGBColor newColor = HSVUtils.hsvToRGB(hsv[0], hsv[1], hsv[2]);

        xfmSpec.setColor(newColor);
        scrollerParams.setXfmSpec(xfmSpec);
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }

    private static void updateValue(ScrollerParams scrollerParams, float[] hsv, RGBColor newColor) {
        scrollerParams.setNewValue("Brightness: " + hsv[2] + " RGB: " + newColor.toString());
    }
}