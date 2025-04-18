package org.xper.allen.rfplot;

import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.HSVUtils;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;

import static org.xper.allen.rfplot.MStickHueScroller.updateValue;

public class MStickSaturationScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T>{

    private static final float SATURATION_INCREMENT = 0.05f; // Adjust as necessary

    public MStickSaturationScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

        float[] hsv = HSVUtils.rgbToHSV(currentColor);

        // Adjust saturation
        hsv[1] += SATURATION_INCREMENT;
        if (hsv[1] > 1.0f) {
            hsv[1] = 1.0f;
        } else if (hsv[1] < 0.0f) {
            hsv[1] = 0.0f;
        }

        RGBColor newColor = HSVUtils.hsvToRGB(hsv);
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

        float[] hsv = HSVUtils.rgbToHSV(currentColor);

        // Adjust saturation
        hsv[1] -= SATURATION_INCREMENT;
        if (hsv[1] > 1.0f) {
            hsv[1] = 1.0f;
        } else if (hsv[1] < 0.0f) {
            hsv[1] = 0.0f;
        }

        RGBColor newColor = HSVUtils.hsvToRGB(hsv);
        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }
}