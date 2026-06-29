package org.xper.allen.noisy;

import org.junit.Before;
import org.junit.Test;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.SplittableRandom;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;
import static org.junit.Assume.assumeTrue;

/**
 * Unit tests / visual examples for {@link CoherenceImageCombiner}, the per-pixel coherence mixing
 * used by the interleaved variant/delta trial type.
 *
 * <p>The statistical/correctness tests run headlessly with no inputs. The "draws_*" tests are visual
 * examples: drop three PNGs into {@link #inputDir} and rerun to get example output written to
 * {@code <inputDir>/coherence_out}. They skip (rather than fail) when the inputs are absent.
 *
 * <p>Expected input files (override the directory with -Dcoherence.test.dir=...):
 * <ul>
 *   <li>{@code coherence_first.png}    - the first shape (e.g. variant)</li>
 *   <li>{@code coherence_second.png}   - the second shape (e.g. delta), same size as the first</li>
 *   <li>{@code coherence_noisemap.png} - the noise map (red channel = noise probability), same size</li>
 * </ul>
 */
public class CoherenceImageCombinerTest {

    /** Where supplied inputs are read from and example output is written. */
    private final String inputDir = System.getProperty("coherence.test.dir", "/home/connorlab/Documents/xper-test");

    private String firstPath;
    private String secondPath;
    private String noiseMapPath;
    private String outDir;

    /** Stimulus color used for the noise overlay; grayscale (zero saturation) by default. */
    private final Color noiseColor = Color.WHITE;
    /** Background the example frames are flattened over (black, matching the default noise background). */
    private final Color background = Color.BLACK;

    @Before
    public void setUp() {
        firstPath = inputDir + "/coherence_first.png";
        secondPath = inputDir + "/coherence_second.png";
        noiseMapPath = inputDir + "/coherence_noisemap.png";
        outDir = inputDir + "/coherence_out";
    }

    // ---------------------------------------------------------------------
    // Always-run correctness tests (no input files needed)
    // ---------------------------------------------------------------------

    @Test
    public void proportionForCoherence_mapsSignedRangeToZeroOne() {
        assertEquals(1.0, CoherenceImageCombiner.proportionForCoherence(1.0), 1e-9);
        assertEquals(0.0, CoherenceImageCombiner.proportionForCoherence(-1.0), 1e-9);
        assertEquals(0.5, CoherenceImageCombiner.proportionForCoherence(0.0), 1e-9); // 0% coherence anchor
        // out-of-range coherence is clamped
        assertEquals(1.0, CoherenceImageCombiner.proportionForCoherence(5.0), 1e-9);
        assertEquals(0.0, CoherenceImageCombiner.proportionForCoherence(-5.0), 1e-9);
    }

    @Test
    public void combine_atProportionOne_returnsFirstImage() {
        BufferedImage first = solid(16, 16, 0xFFFF0000);  // red
        BufferedImage second = solid(16, 16, 0xFF0000FF); // blue
        BufferedImage out = CoherenceImageCombiner.combine(first, second, 1.0, new SplittableRandom(1));
        assertAllPixelsEqual(first, out);
    }

    @Test
    public void combine_atProportionZero_returnsSecondImage() {
        BufferedImage first = solid(16, 16, 0xFFFF0000);
        BufferedImage second = solid(16, 16, 0xFF0000FF);
        BufferedImage out = CoherenceImageCombiner.combine(first, second, 0.0, new SplittableRandom(1));
        assertAllPixelsEqual(second, out);
    }

    @Test
    public void combine_atHalf_isApproximatelyBalanced() {
        int w = 200, h = 200;
        BufferedImage first = solid(w, h, 0xFFFF0000);
        BufferedImage second = solid(w, h, 0xFF0000FF);
        BufferedImage out = CoherenceImageCombiner.combine(first, second, 0.5, new SplittableRandom(42));

        int fromFirst = 0;
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                if (out.getRGB(x, y) == first.getRGB(x, y)) {
                    fromFirst++;
                }
            }
        }
        double fraction = fromFirst / (double) (w * h);
        // 40,000 pixels: the realised fraction should sit very close to 0.5
        assertTrue("expected ~0.5 of pixels from first, got " + fraction, Math.abs(fraction - 0.5) < 0.02);
    }

    @Test
    public void combine_rejectsMismatchedSizes() {
        BufferedImage first = solid(16, 16, 0xFFFFFFFF);
        BufferedImage second = solid(16, 8, 0xFFFFFFFF);
        try {
            CoherenceImageCombiner.combine(first, second, 0.5, new SplittableRandom(1));
            fail("expected IllegalArgumentException for mismatched image sizes");
        } catch (IllegalArgumentException expected) {
            // good
        }
    }

    @Test
    public void applyNoise_atFullProbability_replacesEveryPixel() {
        int w = 64, h = 64;
        BufferedImage base = solid(w, h, 0xFFFF0000);          // solid red shape
        BufferedImage fullNoise = solid(w, h, 0xFFFF0000);     // red channel 255 -> p(noise) = 1
        BufferedImage out = CoherenceImageCombiner.applyNoise(base, fullNoise, noiseColor, background, new SplittableRandom(7));
        // With grayscale noise, every replaced pixel has R == G == B; none should remain pure red.
        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int rgb = out.getRGB(x, y);
                int r = (rgb >> 16) & 0xFF, g = (rgb >> 8) & 0xFF, b = rgb & 0xFF;
                assertEquals("noise pixel should be grayscale", r, g);
                assertEquals("noise pixel should be grayscale", g, b);
            }
        }
    }

    // ---------------------------------------------------------------------
    // Visual examples (require supplied input PNGs; skipped otherwise)
    // ---------------------------------------------------------------------

    @Test
    public void draws_coherence_sweep() throws IOException {
        assumeInputsPresent();
        BufferedImage first = ImageIO.read(new File(firstPath));
        BufferedImage second = ImageIO.read(new File(secondPath));
        BufferedImage noiseMap = ImageIO.read(new File(noiseMapPath));
        new File(outDir).mkdirs();

        double[] proportions = {1.0, 0.75, 0.5, 0.25, 0.0};
        for (double proportion : proportions) {
            String tag = String.format("p%02d", Math.round(proportion * 100));
            BufferedImage mixed = CoherenceImageCombiner.combine(first, second, proportion, new SplittableRandom(0));
            savePng(mixed, outDir + "/sweep_" + tag + "_mixed.png");

            BufferedImage withNoise = CoherenceImageCombiner.applyNoise(
                    mixed, noiseMap, noiseColor, background, new SplittableRandom(0));
            savePng(withNoise, outDir + "/sweep_" + tag + "_noised.png");
        }
        System.out.println("Wrote coherence sweep examples to " + outDir);
    }

    @Test
    public void draws_dynamic_frames_at_zero_coherence() throws IOException {
        assumeInputsPresent();
        BufferedImage first = ImageIO.read(new File(firstPath));
        BufferedImage second = ImageIO.read(new File(secondPath));
        BufferedImage noiseMap = ImageIO.read(new File(noiseMapPath));
        new File(outDir).mkdirs();

        int numFrames = 6;
        for (int i = 0; i < numFrames; i++) {
            // Fresh seed per frame -> the dither re-randomises, as it would during presentation.
            BufferedImage mixed = CoherenceImageCombiner.combine(first, second, 0.5, new SplittableRandom(i));
            BufferedImage withNoise = CoherenceImageCombiner.applyNoise(
                    mixed, noiseMap, noiseColor, background, new SplittableRandom(1000 + i));
            savePng(withNoise, outDir + String.format("/zerocoherence_frame%02d.png", i));
        }
        System.out.println("Wrote " + numFrames + " dynamic 0%-coherence frames to " + outDir);
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    private void assumeInputsPresent() {
        boolean present = new File(firstPath).exists()
                && new File(secondPath).exists()
                && new File(noiseMapPath).exists();
        assumeTrue("Supply " + firstPath + ", " + secondPath + " and " + noiseMapPath
                + " to generate visual examples", present);
    }

    private static BufferedImage solid(int width, int height, int argb) {
        BufferedImage img = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                img.setRGB(x, y, argb);
            }
        }
        return img;
    }

    private static void assertAllPixelsEqual(BufferedImage expected, BufferedImage actual) {
        assertEquals(expected.getWidth(), actual.getWidth());
        assertEquals(expected.getHeight(), actual.getHeight());
        for (int y = 0; y < expected.getHeight(); y++) {
            for (int x = 0; x < expected.getWidth(); x++) {
                assertEquals("pixel mismatch at " + x + "," + y, expected.getRGB(x, y), actual.getRGB(x, y));
            }
        }
    }

    private static void savePng(BufferedImage img, String path) throws IOException {
        ImageIO.write(img, "png", new File(path));
    }
}
