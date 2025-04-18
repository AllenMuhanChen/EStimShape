package org.xper.rfplot.gui.scroller;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.GaborSpec;
import org.xper.rfplot.drawing.png.HSLUtils;

import static org.xper.rfplot.drawing.png.HSLUtils.isPureWhite;


public class GaborHueScroller<T extends GaborSpec> extends RFPlotScroller<T>{
    private static final float HUE_INCREMENT = 15f;
    private boolean isWhite = false;
    public GaborHueScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams)
    {
        RGBColor currentColor = getCurrentColor(scrollerParams);
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
        setNewColor(scrollerParams, newColor);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RGBColor currentColor = getCurrentColor(scrollerParams);
        float[] hsv = HSLUtils.rgbToHSV(currentColor);
        System.out.println("Current HSV: " + hsv[0] + ", " + hsv[1] + ", " + hsv[2]);
        if (Math.round(hsv[0]) == 0f && !isWhite) {
            System.out.println("Setting to White");
            hsv[0] = 360-HUE_INCREMENT;
            hsv[1] = 0f;
            isWhite = true;
        }
        else if (isWhite) {
            System.out.println("Setting White to First Hue");
            hsv[0] = 360-HUE_INCREMENT;
            hsv[1] = 1f;
            isWhite = false;
        } else {
            hsv[0] = HSLUtils.adjustHue(hsv[0], -HUE_INCREMENT);
        }

        RGBColor newColor = HSLUtils.hsvToRGB(hsv);
        setNewColor(scrollerParams, newColor);
        return scrollerParams;
    }

    private void setNewColor(ScrollerParams scrollerParams, RGBColor newColor) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        currentGaborSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(currentGaborSpec.toXml());
    }

    private RGBColor getCurrentColor(ScrollerParams scrollerParams) {
        T currentGaborSpec = getCurrentSpec(scrollerParams);
        RGBColor currentColor = currentGaborSpec.getColor();
        return currentColor;
    }

}