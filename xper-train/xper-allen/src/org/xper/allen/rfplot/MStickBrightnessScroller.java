package org.xper.allen.rfplot;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.HSLUtils;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import static org.xper.allen.rfplot.MStickHueScroller.updateValue;

public class MStickBrightnessScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {

    private static final float BRIGHTNESS_INCREMENT = 0.05f;  // Adjust this value based on your needs
    public MStickBrightnessScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();


        float[] hsv = HSLUtils.rgbToHSV(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsv[2] = HSLUtils.adjustLightness(hsv[2], BRIGHTNESS_INCREMENT);

        RGBColor newColor = HSLUtils.hsvToRGB(hsv[0], hsv[1], hsv[2]);

        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

        float[] hsv = HSLUtils.rgbToHSV(currentColor.getRed(), currentColor.getGreen(), currentColor.getBlue());
        hsv[2] = HSLUtils.adjustLightness(hsv[2], -BRIGHTNESS_INCREMENT);

        RGBColor newColor = HSLUtils.hsvToRGB(hsv[0], hsv[1], hsv[2]);

        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }
}