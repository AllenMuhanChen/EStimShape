package org.xper.allen.noisy;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.lwjgl.opengl.GL11;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.Drawable;
import org.xper.drawing.TestDrawingWindow;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.util.ThreadUtil;

import java.awt.Color;
import java.io.File;
import java.io.FileOutputStream;

import static org.junit.Assume.assumeTrue;

/**
 * OpenGL-context test / visual example for {@link CoherenceNoisyTranslatableImages}. It drives the
 * real GL draw path (per-frame texture upload + dynamic noise overlay) exactly as
 * {@code NoisyNAFCPngScene#drawSample} would, animating the stimulus on screen at frame rate so the
 * dynamic dither can be watched, and saving the first few frames to PNGs for offline inspection.
 *
 * <p>Uses the same inputs as {@link CoherenceImageCombinerTest} (override the directory with
 * {@code -Dcoherence.test.dir=...}); skips rather than fails when they are absent:
 * <ul>
 *   <li>{@code coherence_first.png}    - the first shape (e.g. variant)</li>
 *   <li>{@code coherence_second.png}   - the second shape (e.g. delta), same size as the first</li>
 *   <li>{@code coherence_noisemap.png} - the noise map (red channel = noise probability), same size</li>
 * </ul>
 * Output is written to {@code <inputDir>/coherence_out_gl}. Presentation length and frame rate can be
 * overridden with {@code -Dcoherence.test.seconds=...} and {@code -Dcoherence.test.fps=...}.
 */
public class CoherenceNoisyTranslatableImagesGLTest {

    private static final int SIZE = 1024;
    /** On-screen stimulus size in degrees. */
    private static final double STIM_DEGREES = 35;
    /** How many of the rendered frames to also save as PNGs. */
    private static final int FRAMES_TO_SAVE = 0;

    private final String inputDir = System.getProperty("coherence.test.dir", "/home/connorlab/Documents/xper-test");
    /** On-screen presentation length, in seconds (at least 5 by default so it is actually watchable). */
    private final double presentationSeconds = Double.parseDouble(System.getProperty("coherence.test.seconds", "1"));
    private final int frameRate = Integer.parseInt(System.getProperty("coherence.test.fps", "60"));

    private String firstPath;
    private String secondPath;
    private String noiseMapPath;
    private String outDir;

    private final Coordinates2D location = new Coordinates2D(0, 0);
    private final ImageDimensions dimensions = new ImageDimensions(STIM_DEGREES, STIM_DEGREES);
    private final Color color = new Color(127,255,0);

    private TestDrawingWindow window;
    private PerspectiveRenderer renderer;
    private Context context;

    @Before
    public void setUp() {
        firstPath = inputDir + "/coherence_first.png";
        secondPath = inputDir + "/coherence_second.png";
        noiseMapPath = inputDir + "/coherence_noisemap.png";
        outDir = inputDir + "/coherence_out_gl";

        // Creates the GL context (and loads the native libs). We then drive drawing through the
        // xper PerspectiveRenderer + Context, which is the renderer type NoisyNAFCPngScene uses.
        window = TestDrawingWindow.createDrawerWindow(SIZE, SIZE);
        double dpmm = window.getDpmm();
        renderer = new PerspectiveRenderer();
        renderer.setDistance(500);
        renderer.setPupilDistance(34);
        renderer.setWidth(SIZE / dpmm);
        renderer.setHeight(SIZE / dpmm);
        renderer.setDepth(10000);
        renderer.init(SIZE, SIZE);
        context = new Context();
    }

    @After
    public void tearDown() {
        if (window != null) {
            window.close();
        }
    }

    /**
     * Present a fixed 0% coherence stimulus on screen for {@link #presentationSeconds}
     * at {@link #frameRate}. Each frame the sample texture is a freshly drawn mixture and the noise is
     * refreshed, so the dither visibly moves while the net evidence stays balanced (by visible area,
     * even if the two shapes differ in size). The first {@link #FRAMES_TO_SAVE} frames are also
     * written to PNGs.
     */
    @Test
    public void presents_dynamic_zero_coherence_through_opengl() throws Exception {
        assumeInputsPresent();
        new File(outDir).mkdirs();

        CoherenceNoisyTranslatableImages images = newImages(0.0);
        present(images, "gl_zerocoherence_frame");
        images.cleanUpImage();
        System.out.println("Presented dynamic 0%-coherence for " + presentationSeconds + "s; first "
                + FRAMES_TO_SAVE + " frames saved to " + outDir);
    }

    /**
     * Sweep the signed coherence from all-first (+1) through the balanced 0% anchor to all-second (-1),
     * presenting each level for an equal share of {@link #presentationSeconds} so the whole sweep lasts
     * the full duration.
     */
    @Test
    public void presents_coherence_sweep_through_opengl() throws Exception {
        assumeInputsPresent();
        new File(outDir).mkdirs();

        double[] coherences = {1.0, 0.5, 0.0, -0.5, -1.0};
        double secondsEach = presentationSeconds / coherences.length;
        for (double coherence : coherences) {
            CoherenceNoisyTranslatableImages images = newImages(coherence);
            String tag = String.format("c%+04d", Math.round(coherence * 100));
            present(images, secondsEach, "gl_sweep_" + tag);
            images.cleanUpImage();
        }
        System.out.println("Presented coherence sweep over " + presentationSeconds + "s to " + outDir);
    }

    /**
     * Build the images object for a given signed coherence, pre-generating one distinct frame per
     * presentation frame (capped) so the dither does not visibly loop, plus matching dynamic noise
     * frames.
     */
    private CoherenceNoisyTranslatableImages newImages(double coherence) {
        int distinctFrames = Math.min(120, Math.max(1, (int) Math.round(presentationSeconds * frameRate)));
        CoherenceNoisyTranslatableImages images =
                new CoherenceNoisyTranslatableImages(distinctFrames, 1, 1.0, distinctFrames);
        images.initTextures();
        images.loadCoherenceSample(firstPath, secondPath, coherence, color, 12345L);
        images.loadNoise(noiseMapPath, color);
        return images;
    }

    private void present(CoherenceNoisyTranslatableImages images, String savePrefix) throws Exception {
        present(images, presentationSeconds, savePrefix);
    }

    /** Animate the coherence stimulus on screen for {@code seconds}, saving the first frames as PNGs. */
    private void present(final CoherenceNoisyTranslatableImages images, double seconds, String savePrefix) throws Exception {
        int totalFrames = Math.max(1, (int) Math.round(seconds * frameRate));
        long frameMillis = Math.round(1000.0 / frameRate);
        for (int i = 0; i < totalFrames; i++) {
            GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);
            renderer.draw(new Drawable() {
                @Override
                public void draw(Context c) {
                    images.drawCoherenceSample(true, c, location, dimensions);
                }
            }, context);

            if (savePrefix != null && i < FRAMES_TO_SAVE) {
                // Read the back buffer (before the swap) and write it out.
                byte[] png = AllenPNGMaker.screenShotBinary(SIZE, SIZE);
                try (FileOutputStream fos = new FileOutputStream(outDir + "/" + savePrefix + String.format("%02d", i) + ".png")) {
                    fos.write(png);
                }
            }
            window.window.swapBuffers();
            ThreadUtil.sleep(frameMillis);
        }
    }

    private void assumeInputsPresent() {
        boolean present = new File(firstPath).exists()
                && new File(secondPath).exists()
                && new File(noiseMapPath).exists();
        assumeTrue("Supply " + firstPath + ", " + secondPath + " and " + noiseMapPath
                + " to run the OpenGL coherence example", present);
    }
}
