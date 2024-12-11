package org.xper.drawing;

public class ColorUtils {
    /**
     * Gets the luminance (lightness) value of an RGB color
     * @param color The RGB color to analyze
     * @return The luminance value between 0-1
     */
    public static float getLuminance(RGBColor color) {
        float[] hsl = rgbToHsl(color.getRed(), color.getGreen(), color.getBlue());
        return hsl[2];
    }

    /**
     * Adjusts the luminance of an RGB color while preserving hue and saturation
     * @param originalColor The original RGB color to modify
     * @param luminanceChange Value between 0-1 where 0 is black and 1 is white
     * @return A new RGBColor with modified luminance
     */
    public static RGBColor changeLuminance(RGBColor originalColor, double luminanceChange) {
        // Convert RGB to HSL
        float[] hsl = rgbToHsl(originalColor.getRed(), originalColor.getGreen(), originalColor.getBlue());

        // Modify luminance (lightness)
        hsl[2] = (float) luminanceChange;

        // Convert back to RGB
        float[] rgb = hslToRgb(hsl[0], hsl[1], hsl[2]);

        return new RGBColor(rgb[0], rgb[1], rgb[2]);
    }

    private static float[] rgbToHsl(float r, float g, float b) {
        float max = Math.max(Math.max(r, g), b);
        float min = Math.min(Math.min(r, g), b);
        float h, s, l;

        // Calculate lightness
        l = (max + min) / 2f;

        if (max == min) {
            h = s = 0; // achromatic
        } else {
            float d = max - min;
            s = l > 0.5f ? d / (2f - max - min) : d / (max + min);

            if (max == r) {
                h = (g - b) / d + (g < b ? 6 : 0);
            } else if (max == g) {
                h = (b - r) / d + 2;
            } else {
                h = (r - g) / d + 4;
            }
            h /= 6;
        }

        return new float[]{h, s, l};
    }

    private static float[] hslToRgb(float h, float s, float l) {
        float r, g, b;

        if (s == 0) {
            r = g = b = l; // achromatic
        } else {
            float q = l < 0.5f ? l * (1 + s) : l + s - l * s;
            float p = 2 * l - q;
            r = hueToRgb(p, q, h + 1f/3f);
            g = hueToRgb(p, q, h);
            b = hueToRgb(p, q, h - 1f/3f);
        }

        return new float[]{r, g, b};
    }

    private static float hueToRgb(float p, float q, float t) {
        if (t < 0) t += 1;
        if (t > 1) t -= 1;
        if (t < 1f/6f) return p + (q - p) * 6f * t;
        if (t < 1f/2f) return q;
        if (t < 2f/3f) return p + (q - p) * (2f/3f - t) * 6f;
        return p;
    }
}