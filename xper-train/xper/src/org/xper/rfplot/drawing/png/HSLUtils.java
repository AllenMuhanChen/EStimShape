package org.xper.rfplot.drawing.png;


import org.xper.drawing.RGBColor;

public class HSLUtils {

    public static float[] rgbToHSL(RGBColor color){
        return rgbToHSL(color.getRed(), color.getGreen(), color.getBlue());
    }

    public static float[] rgbToHSL(float r, float g, float b) {
        float max = Math.max(r, Math.max(g, b));
        float min = Math.min(r, Math.min(g, b));
        float h, s, l;
        l = (max + min) / 2.0f;

        if (max == min) {
            h = s = 0; // achromatic
        } else {
            float delta = max - min;
            s = l > 0.5f ? delta / (2.0f - max - min) : delta / (max + min);

            if (max == r) {
                h = (g - b) / delta + (g < b ? 6.0f : 0);
            } else if (max == g) {
                h = 2.0f + (b - r) / delta;
            } else {
                h = 4.0f + (r - g) / delta;
            }

            h /= 6.0f;
        }

        return new float[]{h, s, l};
    }

    public static RGBColor hslToRGB(float[] hsl) {
        return hslToRGB(hsl[0], hsl[1], hsl[2]);
    }

    public static RGBColor hslToRGB(float h, float s, float l) {
        float r, g, b;

        if (s == 0) {
            r = g = b = l; // achromatic
        } else {
            float q = l < 0.5f ? l * (1 + s) : l + s - l * s;
            float p = 2 * l - q;
            r = hueToRGB(p, q, h + 1.0f / 3.0f);
            g = hueToRGB(p, q, h);
            b = hueToRGB(p, q, h - 1.0f / 3.0f);
        }

        return new RGBColor(r, g, b);
    }

    private static float hueToRGB(float p, float q, float t) {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1.0f / 6.0f) return p + (q - p) * 6.0f * t;
        if (t < 1.0f / 2.0f) return q;
        if (t < 2.0f / 3.0f) return p + (q - p) * (2.0f / 3.0f - t) * 6.0f;
        return p;
    }

    public static float adjustHue(float hue, float delta) {
        hue += delta;
        while (hue < 0.0f) hue += 1.0f;
        while (hue >= 1.0f) hue -= 1.0f;
        System.out.println("HSLUtils: adjustHue: " + hue);
        return hue;
    }

    public static float adjustLightness(float lightness, float delta) {
        return clamp(lightness + delta, 0.0f, 1.0f);
    }

    public static float adjustSaturation(float saturation, float delta) {
        return clamp(saturation + delta, 0.0f, 1.0f);
    }

    private static float clamp(float val, float min, float max) {
        return Math.max(min, Math.min(max, val));
    }

    public static boolean isPureWhite(RGBColor color) {
        return color.getRed() == 1.0f && color.getGreen() == 1.0f && color.getBlue() == 1.0f;
    }

}