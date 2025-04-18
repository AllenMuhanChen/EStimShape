package org.xper.rfplot.drawing.png;


import org.xper.drawing.RGBColor;

import java.util.Arrays;

public class HSLUtils {

    public static float[] rgbToHSL(RGBColor color){
        return rgbToHSL(color.getRed(), color.getGreen(), color.getBlue());
    }

    public static float[] rgbToHSV(RGBColor color){
        return rgbToHSV((int)(color.getRed()*255), (int)(color.getGreen()*255), (int)(color.getBlue()*255));
    }

    public static float[] rgbToHSV(int r, int g, int b) {
        float rPrime = r / 255f;
        float gPrime = g / 255f;
        float bPrime = b / 255f;

        float cMax = Math.max(rPrime, Math.max(gPrime, bPrime));
        float cMin = Math.min(rPrime, Math.min(gPrime, bPrime));
        float delta = cMax - cMin;

        float hue = 0;
        if (delta != 0) {
            if (cMax == rPrime) {
                hue = 60 * (((gPrime - bPrime) / delta) % 6);
            } else if (cMax == gPrime) {
                hue = 60 * (((bPrime - rPrime) / delta) + 2);
            } else if (cMax == bPrime) {
                hue = 60 * (((rPrime - gPrime) / delta) + 4);
            }
        }
        hue = (hue < 0) ? hue + 360 : hue;

        float saturation = (cMax == 0) ? 0 : delta / cMax;

        float value = cMax;

        return new float[]{hue, saturation, value};
    }

    public static float[] rgbToHSV(float r, float g, float b) {
        return rgbToHSV((int)(r*255), (int)(g*255), (int)(b*255));
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
    public static RGBColor hsvToRGB(float[] hsv) {
        return hsvToRGB(hsv[0], hsv[1], hsv[2]);
    }

    public static RGBColor hsvToRGB(float h, float s, float v) {
        float r = 0, g = 0, b = 0;

        if (s == 0) {
            r = g = b = v; // achromatic
        } else {
            float c = v * s; // chroma
            float x = c * (1 - Math.abs(((h / 60.0f) % 2) - 1));
            float m = v - c;

            if (h >= 0 && h < 60) {
                r = c;
                g = x;
                b = 0;
            } else if (h >= 60 && h < 120) {
                r = x;
                g = c;
                b = 0;
            } else if (h >= 120 && h < 180) {
                r = 0;
                g = c;
                b = x;
            } else if (h >= 180 && h < 240) {
                r = 0;
                g = x;
                b = c;
            } else if (h >= 240 && h < 300) {
                r = x;
                g = 0;
                b = c;
            } else {
                r = c;
                g = 0;
                b = x;
            }

            r += m;
            g += m;
            b += m;
        }

        return new RGBColor(r, g, b);
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
        hue = Math.round(hue);
        if (hue > 360){
            hue -= 360;
        } else if (hue < 0){
            hue += 360;
        }
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

    public static void main(String[] args) {
        RGBColor inputColor = new RGBColor(1.0f, 0.0f, 0.0f);
        float[] hsv = HSLUtils.rgbToHSV(inputColor);
        System.out.println("HSV: " + Arrays.toString(hsv)); // Should print ~[60, 1, 1]
        hsv[2] = 1f; // Reduce brightness to 50%
        RGBColor convertedBackColor = HSLUtils.hsvToRGB(hsv);
        System.out.println("RGB: " + convertedBackColor.getRed() + ", " + convertedBackColor.getGreen() + ", " + convertedBackColor.getBlue());
// Should print ~[0.5, 0.5, 0]
    }

}