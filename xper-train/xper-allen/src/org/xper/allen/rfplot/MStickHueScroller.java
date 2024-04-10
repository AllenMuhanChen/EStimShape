package org.xper.allen.rfplot;

import org.xper.rfplot.drawing.png.HSLUtils;
import org.xper.rfplot.gui.scroller.RFPlotScroller;
import org.xper.rfplot.gui.scroller.ScrollerParams;
import org.xper.drawing.RGBColor;

import static org.xper.rfplot.drawing.png.HSLUtils.isPureWhite;

public class MStickHueScroller<T extends RFPlotMatchStick.RFPlotMatchStickSpec> extends RFPlotScroller<T> {
    private static final float HUE_INCREMENT = 0.05f;

    public MStickHueScroller(Class<T> type) {
        this.type = type;
    }

    @Override
    public ScrollerParams next(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

        float[] hsl = HSLUtils.rgbToHSL(currentColor);

        if (isPureWhite(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
            hsl[2] = 0.5f; // Reduce lightness to allow color to show
        } else if (isGrayscale(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
        } else {
            hsl[0] = HSLUtils.adjustHue(hsl[0], HUE_INCREMENT);
        }

        RGBColor newColor = HSLUtils.hslToRGB(hsl);
        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }

    @Override
    public ScrollerParams previous(ScrollerParams scrollerParams) {
        RFPlotMatchStick.RFPlotMatchStickSpec currentSpec = getCurrentSpec(scrollerParams);
        RFPlotMatchStick.RFPlotMatchStickSpec newSpec = new RFPlotMatchStick.RFPlotMatchStickSpec(currentSpec);
        RGBColor currentColor = currentSpec.getColor();

        float[] hsl = HSLUtils.rgbToHSL(currentColor);

        if (isPureWhite(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], -HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
            hsl[2] = 0.5f; // Reduce lightness to allow color to show
        } else if (isGrayscale(currentColor)) {
            hsl[0] = HSLUtils.adjustHue(hsl[0], -HUE_INCREMENT);
            hsl[1] = 1.0f; // Set saturation to max
        } else {
            hsl[0] = HSLUtils.adjustHue(hsl[0], -HUE_INCREMENT);
        }

        RGBColor newColor = HSLUtils.hslToRGB(hsl);
        newSpec.setColor(newColor);
        scrollerParams.getRfPlotDrawable().setSpec(newSpec.toXml());
        updateValue(scrollerParams, hsl, newColor);
        return scrollerParams;
    }



    public static void updateValue(ScrollerParams scrollerParams, float[] hsl, RGBColor newColor) {
        // Assuming hsl[0] is the hue component you're interested in formatting
        // Note: The term HSV might have been used interchangeably with HSL by mistake.
        // If you're working with HSV specifically, ensure the input reflects that.
        String formattedHSL = String.format("HSL: %.2f, %.2f, %.2f", hsl[0], hsl[1], hsl[2]);

        // Extract RGB values as integers
        int red = (int) (newColor.getRed() * 255);   // Replace with newColor.red if fields are public
        int green = (int) (newColor.getGreen() * 255); // Replace with newColor.green
        int blue = (int) (newColor.getBlue() * 255);   // Replace with newColor.blue


        // Concatenate the formatted string
        String newValue = formattedHSL + " RGB: " + red + ", " + green + ", " + blue;

        // Update the scrollerParams with the new value
        scrollerParams.setNewValue(newValue);
    }
    private boolean isGrayscale(RGBColor color) {
        return color.getRed() == color.getGreen() && color.getGreen() == color.getBlue();
    }

}