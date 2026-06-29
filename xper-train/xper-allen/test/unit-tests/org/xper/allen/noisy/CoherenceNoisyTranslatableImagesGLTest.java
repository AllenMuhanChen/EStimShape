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

import java.awt.Color;
import java.io.File;
import java.io.FileOutputStream;

import static org.junit.Assume.assumeTrue;

/**
 * OpenGL-context test / visual example for {@link CoherenceNoisyTranslatableImages}. It drives the
 * real GL draw path (per-frame texture upload + dynamic noise overlay) exactly as
 * {@code NoisyNAFCPngScene#drawSample} would, then reads the framebuffer back to PNGs so the dynamic
 * coherence stimulus can be inspected frame by frame.
 *
 * <p>Uses the same inputs as {@link CoherenceImageCombinerTest} (override the directory with
 * {@code -Dcoherence.test.dir=...}); skips rather than fails when they are absent:
 * <ul>
 *   <li>{@code coherence_first.png}    - the first shape (e.g. variant)</li>
 *   <li>{@code coherence_second.png}   - the second shape (e.g. delta), same size as the first</li>
 *   <li>{@code coherence_noisemap.png} - the noise map (red channel = noise probability), same size</li>
 * </ul>
 * Output is written to {@code <inputDir>/coherence_out_gl}.
 */
public class CoherenceNoisyTranslatableImagesGLTest {

    private static final int SIZE = 512;
    /** On-screen stimulus size in degrees. */
    private static final double STIM_DEGREES = 8.0;

    private final String inputDir = System.getProperty("coherence.test.dir", "/home/connorlab/Documents/xper-test");
    private String firstPath;
    private String secondPath;
    private String noiseMapPath;
    private String outDir;

    private final Coordinates2D location = new Coordinates2D(0, 0);
    private final ImageDimensions dimensions = new ImageDimensions(STIM_DEGREES, STIM_DEGREES);
    private final Color color = Color.WHITE;

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
     * Render a sequence of frames at 0% coherence (proportion 0.5). Each frame the sample texture is
     * a freshly drawn mixture and the noise is refreshed, so the saved PNGs should differ frame to
     * frame even though the coherence is fixed.
     */
    @Test
    public void draws_dynamic_zero_coherence_through_opengl() throws Exception {
        assumeInputsPresent();
        new File(outDir).mkdirs();

        int numNoiseFrames = 24;
        int numSampleFrames = 8;
        CoherenceNoisyTranslatableImages images =
                new CoherenceNoisyTranslatableImages(numNoiseFrames, 1, 1.0, numSampleFrames);
        images.initTextures();
        images.loadCoherenceSample(firstPath, secondPath, 0.5, color, 12345L);
        images.loadNoise(noiseMapPath, color);

        for (int i = 0; i < numSampleFrames; i++) {
            renderAndSave(images, outDir + String.format("/gl_zerocoherence_frame%02d.png", i));
        }
        images.cleanUpImage();
        System.out.println("Wrote " + numSampleFrames + " GL 0%-coherence frames to " + outDir);
    }

    /**
     * Render one frame at each of several coherences (proportion of pixels from the first shape) to
     * show the sweep from pure-second through balanced to pure-first, all through the GL path.
     */
    @Test
    public void draws_coherence_sweep_through_opengl() throws Exception {
        assumeInputsPresent();
        new File(outDir).mkdirs();

        double[] proportions = {1.0, 0.75, 0.5, 0.25, 0.0};
        for (double proportion : proportions) {
            CoherenceNoisyTranslatableImages images =
                    new CoherenceNoisyTranslatableImages(8, 1, 1.0, 1);
            images.initTextures();
            images.loadCoherenceSample(firstPath, secondPath, proportion, color, 0L);
            images.loadNoise(noiseMapPath, color);

            String tag = String.format("p%02d", Math.round(proportion * 100));
            renderAndSave(images, outDir + "/gl_sweep_" + tag + ".png");
            images.cleanUpImage();
        }
        System.out.println("Wrote coherence sweep GL frames to " + outDir);
    }

    /** Clear, draw one coherence frame through the renderer/Context, read the framebuffer back to a PNG, then swap. */
    private void renderAndSave(final CoherenceNoisyTranslatableImages images, String path) throws Exception {
        GL11.glClear(GL11.GL_COLOR_BUFFER_BIT | GL11.GL_DEPTH_BUFFER_BIT);
        renderer.draw(new Drawable() {
            @Override
            public void draw(Context c) {
                images.drawCoherenceSample(true, c, location, dimensions);
            }
        }, context);

        byte[] png = AllenPNGMaker.screenShotBinary(SIZE, SIZE);
        try (FileOutputStream fos = new FileOutputStream(path)) {
            fos.write(png);
        }
        window.window.swapBuffers();
    }

    private void assumeInputsPresent() {
        boolean present = new File(firstPath).exists()
                && new File(secondPath).exists()
                && new File(noiseMapPath).exists();
        assumeTrue("Supply " + firstPath + ", " + secondPath + " and " + noiseMapPath
                + " to run the OpenGL coherence example", present);
    }
}
