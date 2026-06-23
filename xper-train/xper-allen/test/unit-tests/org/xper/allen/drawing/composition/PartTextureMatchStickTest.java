package org.xper.allen.drawing.composition;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.util.FileUtil;
import org.xper.util.ResourceUtil;

import javax.imageio.ImageIO;
import java.awt.Color;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;
import static org.xper.drawing.TestDrawingWindow.initXperLibs;

/**
 * Draws a real match stick and runs the part-texture (mixed SHADE/2D) path end to end on the
 * OpenGL window, then verifies the composite genuinely mixes the two textures.
 *
 * <p>Like the other drawing tests in this module, this needs a display, the native LWJGL
 * libraries, a Spring-wired {@link AllenPNGMaker}, and a writable {@code testBin} — so it runs
 * on the rig, not in a headless CI sandbox. The pure pixel logic is covered separately and
 * head-lessly by {@link LimbTextureCompositorTest}; this test exercises the real render passes.
 */
public class PartTextureMatchStickTest {

    /** Per-channel tolerance when checking a composite pixel against a source render (AA/MSAA jitter). */
    private static final int CHANNEL_TOLERANCE = 12;

    private final GaussianNoiseMapper noiseMapper = new GaussianNoiseMapper();
    private AllenPNGMaker pngMaker;
    private String testBin;
    private ProceduralMatchStick mStick;

    @Before
    public void setUp() throws Exception {
        initXperLibs();
        testBin = "/home/connorlab/Documents/xper-test";

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        pngMaker = context.getBean(AllenPNGMaker.class);
        pngMaker.createDrawerWindow();

        mStick = new ProceduralMatchStick(noiseMapper);
        mStick.setProperties(5, "SHADE", 1.0);
        mStick.setStimColor(new Color(255, 255, 255));
        mStick.genMatchStickRand();
        mStick.setMaxAttempts(-1);
    }

    @Test
    public void partTextureCompositeMixesShadeAnd2D() throws Exception {
        int nComponents = mStick.getnComponent();
        assertTrue("need at least 2 components to see a mix, got " + nComponents, nComponents >= 2);

        // Draw the whole shape once all-SHADE and once all-2D, from the same pose.
        mStick.setTextureType("SHADE");
        BufferedImage shadeImg = read(pngMaker.createAndSavePNG(
                mStick, 9001L, Collections.singletonList("partTexture_shade"), testBin));

        mStick.setTextureType("2D");
        BufferedImage twoDImg = read(pngMaker.createAndSavePNG(
                mStick, 9002L, Collections.singletonList("partTexture_2d"), testBin));

        // Draw the part-texture composite: component 1 in 2D, the rest in SHADE.
        Set<Integer> partComponents = new HashSet<>(Arrays.asList(1));
        mStick.setTextureType("SHADE");
        BufferedImage mixedImg = read(pngMaker.createAndSavePartTexturePNG(
                mStick, 9003L, Collections.singletonList("partTexture_mixed"), testBin,
                "SHADE", "2D", partComponents));

        assertEquals(shadeImg.getWidth(), mixedImg.getWidth());
        assertEquals(shadeImg.getHeight(), mixedImg.getHeight());

        int width = mixedImg.getWidth();
        int height = mixedImg.getHeight();

        int matchesShade = 0;     // composite pixel came from (or equals) the SHADE render
        int matchesTwoD = 0;      // composite pixel came from (or equals) the 2D render
        int matchesNeither = 0;   // composite pixel matches neither source (should not happen)
        int differsBetweenSources = 0; // pixels where the two source renders actually differ

        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int mixed = mixedImg.getRGB(x, y);
                int shade = shadeImg.getRGB(x, y);
                int twoD = twoDImg.getRGB(x, y);

                boolean nearShade = close(mixed, shade);
                boolean nearTwoD = close(mixed, twoD);

                if (nearShade) matchesShade++;
                if (nearTwoD) matchesTwoD++;
                if (!nearShade && !nearTwoD) matchesNeither++;
                if (!close(shade, twoD)) differsBetweenSources++;
            }
        }

        long totalPixels = (long) width * height;

        // The compositor only ever copies a pixel from one of the two source renders, so
        // (allowing for AA jitter) essentially every pixel should match at least one source.
        double neitherFraction = matchesNeither / (double) totalPixels;
        assertTrue("too many composite pixels match neither source render: " + matchesNeither
                + " / " + totalPixels, neitherFraction < 0.02);

        // The two sources must actually differ somewhere, otherwise the test proves nothing.
        assertTrue("SHADE and 2D renders are identical; cannot verify mixing", differsBetweenSources > 0);

        // Real mixing: among pixels where the sources differ, the composite must take some from
        // the 2D render (the 2D limb) AND some from the SHADE render (the rest of the shape).
        int mixedFromShadeWhereDiffer = 0;
        int mixedFromTwoDWhereDiffer = 0;
        for (int y = 0; y < height; y++) {
            for (int x = 0; x < width; x++) {
                int shade = shadeImg.getRGB(x, y);
                int twoD = twoDImg.getRGB(x, y);
                if (close(shade, twoD)) continue;
                int mixed = mixedImg.getRGB(x, y);
                if (close(mixed, twoD)) mixedFromTwoDWhereDiffer++;
                else if (close(mixed, shade)) mixedFromShadeWhereDiffer++;
            }
        }
        assertTrue("composite never used the 2D render where it could; 2D limb missing",
                mixedFromTwoDWhereDiffer > 0);
        assertTrue("composite never kept the SHADE render where it could; nothing stayed shaded",
                mixedFromShadeWhereDiffer > 0);
    }

    private static BufferedImage read(String path) throws Exception {
        BufferedImage img = ImageIO.read(new File(path));
        if (img == null) {
            throw new IllegalStateException("could not read rendered image at " + path);
        }
        return img;
    }

    private static boolean close(int argbA, int argbB) {
        return Math.abs(((argbA >> 16) & 0xFF) - ((argbB >> 16) & 0xFF)) <= CHANNEL_TOLERANCE
                && Math.abs(((argbA >> 8) & 0xFF) - ((argbB >> 8) & 0xFF)) <= CHANNEL_TOLERANCE
                && Math.abs((argbA & 0xFF) - (argbB & 0xFF)) <= CHANNEL_TOLERANCE;
    }
}
