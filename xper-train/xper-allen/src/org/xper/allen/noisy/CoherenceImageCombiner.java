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
     * Map a signed coherence in [-1, 1] to {@code proportionFirst} in [0, 1], anchoring the
     * 0% coherence point at a plain 50/50 coin.
     *
     * <p>coherence = +1 -&gt; all first, -1 -&gt; all second, 0 -&gt; 0.5. This is the un-normalized
     * mapping; for shapes of unequal foreground area prefer
     * {@link #proportionForCoherence(double, double)} with {@link #neutralProportionFirst}
     * so that 0% coherence is balanced by <i>visible area</i> rather than by pixel probability.
     */
    public static double proportionForCoherence(double coherence) {
        return proportionForCoherence(coherence, 0.5);
    }

    /**
     * Map a signed coherence in [-1, 1] to {@code proportionFirst} in [0, 1], anchoring the
     * 0% coherence point at {@code neutralProportion} instead of 0.5.
     *
     * <p>The endpoints are preserved (coherence = +1 -&gt; all first, -1 -&gt; all second) while the
     * neutral point is shifted, so that pairing this with {@link #neutralProportionFirst} yields a
     * sample whose <i>expected visible foreground area</i> is equal for the two shapes at 0%
     * coherence, regardless of their relative sizes. The two half-ranges are interpolated linearly:
     * <pre>
     *   coherence &gt;= 0:  p = neutral + coherence * (1 - neutral)
     *   coherence &lt;  0:  p = neutral * (1 + coherence)
     * </pre>
     *
     * @param coherence        signed coherence, clamped to [-1, 1]
     * @param neutralProportion the {@code proportionFirst} that corresponds to 0% coherence, in [0, 1]
     */
    public static double proportionForCoherence(double coherence, double neutralProportion) {
        double c = Math.max(-1.0, Math.min(1.0, coherence));
        double p0 = Math.max(0.0, Math.min(1.0, neutralProportion));
        double proportion = (c >= 0.0) ? p0 + c * (1.0 - p0) : p0 * (1.0 + c);
        return Math.max(0.0, Math.min(1.0, proportion));
    }

    /**
     * The {@code proportionFirst} that balances the two shapes by <i>visible foreground area</i>,
     * i.e. the 0% coherence anchor for shapes of unequal size.
     *
     * <p>Because {@link #combine} draws each pixel whole, the expected visible foreground area of a
     * shape is {@code proportionDrawn * itsForegroundPixelCount}. Setting
     * {@code proportionFirst = areaSecond / (areaFirst + areaSecond)} makes the two expected visible
     * areas equal, so a shape that happens to occupy many more pixels is no longer over-represented
     * at 0% coherence.
     *
     * <p>Foreground is counted as the pixels that differ from the background color, and the
     * background color is taken to be the image's most common pixel value (see
     * {@link #foregroundPixelCount}) — no comp map or alpha channel is needed, and it is robust to
     * whatever flat background the PNG was rendered on. When both images are a single flat color the
     * result falls back to 0.5.
     */
    public static double neutralProportionFirst(BufferedImage first, BufferedImage second) {
        long areaFirst = foregroundPixelCount(first);
        long areaSecond = foregroundPixelCount(second);
        long total = areaFirst + areaSecond;
        if (total <= 0L) {
            return 0.5;
        }
        return areaSecond / (double) total;
    }

    /**
     * Number of foreground pixels in an image: every pixel whose value differs from the background
     * color, where the background is taken to be the image's <i>most common</i> pixel value.
     *
     * <p>The shape is rendered on a flat background that fills the bulk of the image, so the modal
     * color is the background regardless of what color it happens to be. Anti-aliased edge pixels
     * differ from that background and so count as foreground; this slightly inflates the count at the
     * boundary but does so symmetrically for both shapes, which is all the area ratio depends on.
     */
    public static long foregroundPixelCount(BufferedImage img) {
        int background = backgroundColor(img);
        int width = img.getWidth();
        int height = img.getHeight();
        long foreground = 0L;
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                if (img.getRGB(x, y) != background) {
                    foreground++;
                }
            }
        }
        return foreground;
    }

    /** The most common pixel value in the image, taken to be its flat background color. */
    public static int backgroundColor(BufferedImage img) {
        int width = img.getWidth();
        int height = img.getHeight();
        java.util.Map<Integer, Integer> counts = new java.util.HashMap<>();
        int background = img.getRGB(0, 0);
        int bestCount = 0;
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int argb = img.getRGB(x, y);
                int count = counts.merge(argb, 1, Integer::sum);
                if (count > bestCount) {
                    bestCount = count;
                    background = argb;
                }
            }
        }
        return background;
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
