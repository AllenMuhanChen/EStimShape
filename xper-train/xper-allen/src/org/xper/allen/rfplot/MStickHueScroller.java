package org.xper.allen.rfplot;

import org.xper.rfplot.drawing.png.HSLUtils;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;
import org.xper.drawing.RGBColor;

import static org.xper.rfplot.drawing.png.HSLUtils.isPureWhite;

public class MStickHueScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {
    private static final float HUE_INCREMENT = 15f;

    private boolean isWhite = false;
    public MStickHueScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

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
        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsv, newColor);
        return scrollerParams;
    }



    public static void updateValue(ScrollerParams scrollerParams, float[] hsv, RGBColor newColor) {
        String formattedHSV = String.format("HSV: %.2f, %.2f, %.2f", hsv[0], hsv[1], hsv[2]);

        // Extract RGB values as integers
        int red = (int) (newColor.getRed() * 255);   // Replace with newColor.red if fields are public
        int green = (int) (newColor.getGreen() * 255); // Replace with newColor.green
        int blue = (int) (newColor.getBlue() * 255);   // Replace with newColor.blue


        // Concatenate the formatted string
        String newValue = formattedHSV + " RGB: " + red + ", " + green + ", " + blue;

        // Update the scrollerParams with the new value
        scrollerParams.setNewValue(newValue);
    }
    private boolean isGrayscale(RGBColor color) {
        return color.getRed() == color.getGreen() && color.getGreen() == color.getBlue();
    }

}