package org.xper.allen.drawing.composition;

import org.junit.Before;
import org.junit.Test;

import java.awt.image.BufferedImage;
import java.util.Collections;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.fail;

public class LimbTextureCompositorTest {

    // Distinct, easy-to-assert fill colors for the two source renders.
    private static final int PRIMARY_FILL = 0xFF808080;   // gray
    private static final int SECONDARY_FILL = 0xFF0000FF;  // blue
    private static final int BACKGROUND = 0xFF000000;      // black

    private LimbTextureCompositor compositor;
    private Map<Integer, float[]> palette;

    @Before
    public void setUp() {
        compositor = new LimbTextureCompositor();
        // comp 1 -> white, comp 2 -> red, comp 3 -> green
        palette = CompMapColors.paletteFor(3);
    }

    private BufferedImage solid(int width, int height, int argb) {
        BufferedImage img = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                img.setRGB(x, y, argb);
            }
        }
        return img;
    }

    /** Builds a comp map where the left half is one comp color and the right half another. */
    private BufferedImage leftRightCompMap(int width, int height, int leftArgb, int rightArgb) {
        BufferedImage img = new BufferedImage(width, height, BufferedImage.TYPE_INT_ARGB);
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                img.setRGB(x, y, x < width / 2 ? leftArgb : rightArgb);
            }
        }
        return img;
    }

    private static int argbOf(float[] rgb) {
        int r = Math.round(rgb[0] * 255f);
        int g = Math.round(rgb[1] * 255f);
        int b = Math.round(rgb[2] * 255f);
        return 0xFF000000 | (r << 16) | (g << 8) | b;
    }

    private static Set<Integer> setOf(Integer... values) {
        return new HashSet<>(java.util.Arrays.asList(values));
    }

    @Test
    public void secondaryComponentPixelsComeFromSecondary_othersFromPrimary() {
        int w = 4, h = 2;
        BufferedImage primary = solid(w, h, PRIMARY_FILL);
        BufferedImage secondary = solid(w, h, SECONDARY_FILL);
        // left half = comp 1 (white = primary), right half = comp 2 (red = secondary)
        BufferedImage compMap = leftRightCompMap(w, h,
                argbOf(CompMapColors.colorFor(1)), argbOf(CompMapColors.colorFor(2)));

        BufferedImage out = compositor.compose(primary, secondary, compMap, palette, setOf(2));

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                int expected = x < w / 2 ? PRIMARY_FILL : SECONDARY_FILL;
                assertEquals("pixel (" + x + "," + y + ")", expected, out.getRGB(x, y));
            }
        }
    }

    @Test
    public void noSecondaryComponentsMeansAllPrimary() {
        int w = 4, h = 2;
        BufferedImage primary = solid(w, h, PRIMARY_FILL);
        BufferedImage secondary = solid(w, h, SECONDARY_FILL);
        BufferedImage compMap = leftRightCompMap(w, h,
                argbOf(CompMapColors.colorFor(1)), argbOf(CompMapColors.colorFor(2)));

        BufferedImage out = compositor.compose(primary, secondary, compMap, palette,
                Collections.<Integer>emptySet());

        for (int y = 0; y < h; y++) {
            for (int x = 0; x < w; x++) {
                assertEquals(PRIMARY_FILL, out.getRGB(x, y));
            }
        }
    }

    @Test
    public void multipleSecondaryComponents() {
        int w = 3, h = 1;
        BufferedImage primary = solid(w, h, PRIMARY_FILL);
        BufferedImage secondary = solid(w, h, SECONDARY_FILL);
        BufferedImage compMap = new BufferedImage(w, h, BufferedImage.TYPE_INT_ARGB);
        compMap.setRGB(0, 0, argbOf(CompMapColors.colorFor(1))); // primary
        compMap.setRGB(1, 0, argbOf(CompMapColors.colorFor(2))); // secondary
        compMap.setRGB(2, 0, argbOf(CompMapColors.colorFor(3))); // secondary

        BufferedImage out = compositor.compose(primary, secondary, compMap, palette, setOf(2, 3));

        assertEquals(PRIMARY_FILL, out.getRGB(0, 0));
        assertEquals(SECONDARY_FILL, out.getRGB(1, 0));
        assertEquals(SECONDARY_FILL, out.getRGB(2, 0));
    }

    @Test
    public void backgroundPixelsFallBackToPrimary() {
        int w = 2, h = 1;
        BufferedImage primary = solid(w, h, PRIMARY_FILL);
        BufferedImage secondary = solid(w, h, SECONDARY_FILL);
        // both pixels are background (black) in the comp map: not near any palette color
        BufferedImage compMap = solid(w, h, BACKGROUND);

        BufferedImage out = compositor.compose(primary, secondary, compMap, palette, setOf(2));

        assertEquals(PRIMARY_FILL, out.getRGB(0, 0));
        assertEquals(PRIMARY_FILL, out.getRGB(1, 0));
    }

    @Test
    public void antiAliasedBoundaryBlendFallsBackToPrimary() {
        int w = 1, h = 1;
        BufferedImage primary = solid(w, h, PRIMARY_FILL);
        BufferedImage secondary = solid(w, h, SECONDARY_FILL);
        // halfway blend between comp 1 (white) and comp 2 (red) = (255,128,128):
        // ~181 from each, beyond the default threshold -> primary
        BufferedImage compMap = solid(w, h, 0xFFFF8080);

        BufferedImage out = compositor.compose(primary, secondary, compMap, palette, setOf(2));

        assertEquals(PRIMARY_FILL, out.getRGB(0, 0));
    }

    @Test
    public void confidentSecondaryMatchSurvivesSlightNoise() {
        int w = 1, h = 1;
        BufferedImage primary = solid(w, h, PRIMARY_FILL);
        BufferedImage secondary = solid(w, h, SECONDARY_FILL);
        // comp 2 is pure red (255,0,0); nudge slightly -> still well within threshold
        BufferedImage compMap = solid(w, h, 0xFFF00A0A);

        BufferedImage out = compositor.compose(primary, secondary, compMap, palette, setOf(2));

        assertEquals(SECONDARY_FILL, out.getRGB(0, 0));
    }

    @Test
    public void mismatchedDimensionsThrows() {
        BufferedImage primary = solid(4, 4, PRIMARY_FILL);
        BufferedImage secondary = solid(4, 4, SECONDARY_FILL);
        BufferedImage compMap = solid(2, 4, BACKGROUND);
        try {
            compositor.compose(primary, secondary, compMap, palette, setOf(2));
            fail("expected IllegalArgumentException for mismatched dimensions");
        } catch (IllegalArgumentException expected) {
            // ok
        }
    }
}
