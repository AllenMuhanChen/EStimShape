package org.xper.allen.noisy;

import java.awt.Color;
import java.awt.image.BufferedImage;
import java.util.SplittableRandom;

/**
 * Builds the "coherence" sample stimulus for interleaved variant/delta trials.
 *
 * <p>Each output frame is a per-pixel random mixture of two equally sized source images
 * (a "first" and "second" shape, e.g. a variant and a delta). For every pixel we
 * independently draw the pixel from the first image with probability
 * {@code proportionFirst}, otherwise from the second image. At
 * {@code proportionFirst == 0.5} the frame carries zero <i>net</i> evidence toward
 * either shape (the "0% coherence" anchor) while still presenting clear local shape
 * structure at every pixel.
 *
 * <p>Re-drawing a fresh mixture every frame (a new {@link SplittableRandom} seed per
 * frame) produces dynamic dither: the stipple pattern refreshes each frame so it
 * temporally averages into a balanced blend rather than forming a static texture cue
 * sitting on the diagnostic region.
 *
 * <p>This class is intentionally free of any OpenGL dependency so it can be unit tested
 * headlessly. {@link CoherenceNoisyTranslatableImages} wires it into the GL presentation
 * pipeline; {@link #applyNoise} reproduces the production noise overlay on the CPU purely
 * for visualization/testing.
 *
 * @author Allen Chen
 */
public class CoherenceImageCombiner {

    private CoherenceImageCombiner() {
    }

    /**
     * Map a signed coherence in [-1, 1] to {@code proportionFirst} in [0, 1].
     * coherence = +1 -&gt; all first, -1 -&gt; all second, 0 -&gt; balanced (the 0% coherence anchor).
     */
    public static double proportionForCoherence(double coherence) {
        double proportion = (coherence + 1.0) / 2.0;
        return Math.max(0.0, Math.min(1.0, proportion));
    }

    /**
     * Per-pixel Bernoulli mixture of two equally sized RGBA images. Every pixel is taken
     * whole (all four channels) from {@code first} with probability {@code proportionFirst},
     * otherwise from {@code second}, so per-pixel contrast is preserved rather than averaged.
     *
     * @param proportionFirst probability in [0, 1] that a given pixel is drawn from {@code first}
     * @param rng             random source; pass a fresh seed per frame for dynamic dither
     * @throws IllegalArgumentException if the two images differ in size
     */
    public static BufferedImage combine(BufferedImage first, BufferedImage second,
                                        double proportionFirst, SplittableRandom rng) {
        if (first.getWidth() != second.getWidth() || first.getHeight() != second.getHeight()) {
            throw new IllegalArgumentException(
                    "Source images must match in size: first=" + first.getWidth() + "x" + first.getHeight()
                            + " second=" + second.getWidth() + "x" + second.getHeight());
        }
        int width = first.getWidth();
        int height = first.getHeight();
        BufferedImage out = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int argb = (rng.nextDouble() < proportionFirst) ? first.getRGB(x, y) : second.getRGB(x, y);
                out.setRGB(x, y, argb);
            }
        }
        return out;
    }

    /**
     * Overlay noise onto a sample frame for visualization, matching the production semantics in
     * {@link NoisyTranslatableResizableImages}: with probability equal to the noise map's red
     * channel (0-255 -&gt; 0-1) a pixel is replaced by random-lightness noise of {@code noiseColor}
     * (grayscale when {@code noiseColor} has zero saturation, exactly as
     * {@code calculateNoisePixels} does); otherwise the base pixel is kept. Base pixels are
     * composited over {@code background} so the result is a flat, directly viewable image of what
     * the animal would see on a single frame.
     *
     * @throws IllegalArgumentException if the noise map differs in size from the base image
     */
    public static BufferedImage applyNoise(BufferedImage base, BufferedImage noiseMap,
                                           Color noiseColor, Color background, SplittableRandom rng) {
        if (noiseMap.getWidth() != base.getWidth() || noiseMap.getHeight() != base.getHeight()) {
            throw new IllegalArgumentException(
                    "Noise map must match base image size: base=" + base.getWidth() + "x" + base.getHeight()
                            + " noiseMap=" + noiseMap.getWidth() + "x" + noiseMap.getHeight());
        }
        int width = base.getWidth();
        int height = base.getHeight();
        float[] hsb = Color.RGBtoHSB(noiseColor.getRed(), noiseColor.getGreen(), noiseColor.getBlue(), null);
        boolean grayscale = hsb[1] == 0f;
        BufferedImage out = new BufferedImage(width, height, BufferedImage.TYPE_INT_RGB);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                double noiseProbability = ((noiseMap.getRGB(x, y) >> 16) & 0xFF) / 255.0;
                int rgb;
                if (rng.nextDouble() < noiseProbability) {
                    float lightness = (float) rng.nextDouble();
                    float saturation = grayscale ? 0f : (float) rng.nextDouble();
                    rgb = Color.getHSBColor(hsb[0], saturation, lightness).getRGB();
                } else {
                    rgb = flattenOver(base.getRGB(x, y), background);
                }
                out.setRGB(x, y, rgb & 0xFFFFFF);
            }
        }
        return out;
    }

    /** Alpha-composite a single ARGB pixel over an opaque background, returning packed RGB. */
    private static int flattenOver(int argb, Color background) {
        int alpha = (argb >>> 24) & 0xFF;
        if (alpha == 255) {
            return argb & 0xFFFFFF;
        }
        double alphaFraction = alpha / 255.0;
        int sourceRed = (argb >> 16) & 0xFF;
        int sourceGreen = (argb >> 8) & 0xFF;
        int sourceBlue = argb & 0xFF;
        int red = (int) Math.round(sourceRed * alphaFraction + background.getRed() * (1 - alphaFraction));
        int green = (int) Math.round(sourceGreen * alphaFraction + background.getGreen() * (1 - alphaFraction));
        int blue = (int) Math.round(sourceBlue * alphaFraction + background.getBlue() * (1 - alphaFraction));
        return (red << 16) | (green << 8) | blue;
    }
}
