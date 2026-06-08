package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import javax.imageio.ImageIO;
import javax.vecmath.Point3d;
import java.awt.Color;
import java.awt.Graphics2D;
import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;

/**
 * Standalone harness for testing the delta-generation behavior of
 * {@link org.xper.allen.pga.EStimShapeVariantsDeltaStim}.
 *
 * We can't use EStimShapeVariantsDeltaStim directly (it depends on DB-backed managers
 * and a generator), so this test reproduces its {@code createMStick()} logic with a
 * hardcoded parent shape (loaded from file) and hardcoded "special limbs"
 * (the components to mutate in the parent).
 *
 * It generates {@link #NUM_DELTAS} deltas and saves the original + each delta as a PNG
 * to {@link #OUTPUT_DIR} for visual inspection.
 *
 * Goal: tweak the "Generate child" block (see {@link #generateDelta}) to make deltas
 * more likely to be geometrically distinct, then port the winning version back into
 * EStimShapeVariantsDeltaStim.
 */
public class DeltaStimVariantTest {

    // ---------------------------------------------------------------------------------------------
    // EDIT THESE
    // ---------------------------------------------------------------------------------------------

    /** Path to the parent shape spec xml. (You said you'll handle this.) */
    private static final String PARENT_SPEC_PATH = "/home/connorlab/Documents/xper-test/delta-test/parent_spec.xml";

    /** Hardcoded "special limbs": the parent component indices to MUTATE. Everything else is preserved. */
    private static final List<Integer> COMPS_TO_MUTATE_IN_PARENT = new ArrayList<>(Arrays.asList(1));

    /** How many deltas to generate. */
    private static final int NUM_DELTAS = 10;

    /** Where to dump the PNGs. */
    private static final String OUTPUT_DIR = "/home/connorlab/Documents/xper-test/delta-test";

    // Shape rendering / morph properties (mirror EStimShapeVariantsDeltaStim defaults).
    private static final double SIZE_DIAMETER_DEGREES = 3.0;
    private static final double MAX_DIAMETER_DEGREES = 10.0;
    private static final String TEXTURE_TYPE = "SHADE";
    private static final boolean IS_2D = false;
    private static final double CONTRAST = 1.0;
    private static final RGBColor COLOR = new RGBColor(1.0, 0.0, 0.0);

    // ---------------------------------------------------------------------------------------------

    /** Mock receptive field (mirrors GAMatchStickTest.COMPLETE_RF) — the sticks need one. */
    private static final ReceptiveField MOCK_RF = new ReceptiveField() {
        double h = 50;
        double k = 50;
        double r = 20;

        {
            center = new Coordinates2D(h, k);
            radius = r;
            for (int i = 0; i < 100; i++) {
                double angle = 2 * Math.PI * i / 100;
                outline.add(new Coordinates2D(h + r * Math.cos(angle), k + r * Math.sin(angle)));
            }
        }

        @Override
        public boolean isInRF(double x, double y) {
            return (x - h) * (x - h) + (y - k) * (y - k) < r * r;
        }
    };

    private TestMatchStickDrawer drawer;
    private GaussianNoiseMapper noiseMapper;

    @Before
    public void setUp() throws Exception {
        drawer = new TestMatchStickDrawer();
        drawer.setup(500, 500);

        noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setWidth(500);
        noiseMapper.setHeight(500);
        noiseMapper.setBackground(0);
        noiseMapper.setDoEnforceHiddenJunction(true);

        new File(OUTPUT_DIR).mkdirs();
    }

    @Test
    public void generate_and_save_deltas() {
        // --- Load the parent shape from file ---
        PruningMatchStick parentMStick = new PruningMatchStick(noiseMapper);
        parentMStick.setRf(MOCK_RF);
        parentMStick.setProperties(SIZE_DIAMETER_DEGREES, TEXTURE_TYPE, IS_2D, CONTRAST);
        parentMStick.setStimColor(COLOR);
        parentMStick.genMatchStickFromFile(PARENT_SPEC_PATH);

        // Track saved images so we can collate them into one figure at the end.
        List<String> labels = new ArrayList<>();
        List<String> paths = new ArrayList<>();

        // Save the original thumbnail + a component map (the comp map makes it easy to pick
        // which component indices to use as "special limbs").
        drawer.drawThumbnail(parentMStick);
        ThreadUtil.sleep(500);
        labels.add("original");
        paths.add(drawer.saveImage(OUTPUT_DIR + "/original"));
        ThreadUtil.sleep(250);
        drawer.clear();
        drawer.drawCompMap(parentMStick);
        ThreadUtil.sleep(500);
        drawer.saveImage(OUTPUT_DIR + "/original_comp_map");
        ThreadUtil.sleep(250);
        drawer.clear();

        // Components to mutate vs preserve (mirror EStimShapeVariantsDeltaStim).
        List<Integer> compsToMutateInParent = new ArrayList<>(COMPS_TO_MUTATE_IN_PARENT);
        List<Integer> compsToPreserveInParent = new ArrayList<>();
        for (int i = 1; i <= parentMStick.getNComponent(); i++) {
            if (!compsToMutateInParent.contains(i)) {
                compsToPreserveInParent.add(i);
            }
        }

        System.out.println("Parent nComponent: " + parentMStick.getNComponent());
        System.out.println("Comps to mutate:   " + compsToMutateInParent);
        System.out.println("Comps to preserve: " + compsToPreserveInParent);

        for (int deltaIdx = 0; deltaIdx < NUM_DELTAS; deltaIdx++) {
            DeltaResult result = null;
            while (result == null) {
                try {
                    result = generateDelta(parentMStick, compsToMutateInParent, compsToPreserveInParent);
                } catch (Exception e) {
                    System.out.println("Delta " + deltaIdx + " attempt failed, retrying: " + e.getMessage());
                }
            }

            String magStr = String.format("%.2f", result.magnitude);
            drawer.drawThumbnail(result.stick);
            ThreadUtil.sleep(500);
            labels.add("mag " + magStr);
            paths.add(drawer.saveImage(OUTPUT_DIR + "/delta_" + deltaIdx + "_mag_" + magStr));
            ThreadUtil.sleep(250);
            drawer.clear();
            System.out.println("Saved delta " + deltaIdx + " (magnitude=" + magStr + ")");
        }

        // Collate the original + all deltas into a single figure.
        String collagePath = OUTPUT_DIR + "/collage.png";
        collate(labels, paths, collagePath);

        System.out.println("Done. Wrote original + " + NUM_DELTAS + " deltas and collage to " + OUTPUT_DIR);
    }

    /**
     * Tiles the given images into a single labeled grid figure and writes it to {@code outPath}.
     */
    private static void collate(List<String> labels, List<String> paths, String outPath) {
        int cols = 4;
        int cell = 220;          // scaled image size per cell
        int labelH = 18;         // space for the text label above each image
        int pad = 6;             // padding around each cell
        int n = paths.size();
        int rows = (int) Math.ceil(n / (double) cols);

        int cellW = cell + 2 * pad;
        int cellH = cell + labelH + 2 * pad;
        BufferedImage figure = new BufferedImage(cols * cellW, rows * cellH, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = figure.createGraphics();
        g.setColor(Color.BLACK);
        g.fillRect(0, 0, figure.getWidth(), figure.getHeight());

        for (int i = 0; i < n; i++) {
            int row = i / cols;
            int col = i % cols;
            int x = col * cellW + pad;
            int y = row * cellH + pad;

            try {
                BufferedImage img = ImageIO.read(new File(paths.get(i)));
                if (img != null) {
                    g.drawImage(img, x, y, cell, cell, null);
                }
            } catch (IOException e) {
                System.out.println("Could not read " + paths.get(i) + " for collage: " + e.getMessage());
            }

            // Label (magnitude) in white text under the image.
            g.setColor(Color.WHITE);
            g.drawString(labels.get(i), x, y + cell + labelH - 4);
        }
        g.dispose();

        try {
            ImageIO.write(figure, "png", new File(outPath));
            System.out.println("Wrote collage to " + outPath);
        } catch (IOException e) {
            System.out.println("Could not write collage: " + e.getMessage());
        }
    }

    /**
     * Reproduces the child-generation logic from EStimShapeVariantsDeltaStim.createMStick().
     *
     * THIS is the part you're testing — tweak the "Generate child" block below to make deltas
     * more likely to be geometrically distinct, then port the winner back into the real class.
     */
    private DeltaResult generateDelta(PruningMatchStick parentMStick,
                                      List<Integer> compsToMutateInParent,
                                      List<Integer> compsToPreserveInParent) {
        // Position the child so its first preserved comp lands where it was in the parent.
        Point3d toPreserveCompLocation = parentMStick.getComp()[compsToPreserveInParent.get(0)].getMassCenter();
        PruningMatchStick childMStick = new PruningMatchStick(toPreserveCompLocation, noiseMapper);
        childMStick.setRf(MOCK_RF);
        childMStick.setPreservedComps(compsToPreserveInParent);
        childMStick.setToPreserveInParent(compsToPreserveInParent);

        childMStick.setProperties(SIZE_DIAMETER_DEGREES, TEXTURE_TYPE, IS_2D, CONTRAST);
        childMStick.setStimColor(COLOR);
        childMStick.setMaxDiameterDegrees(MAX_DIAMETER_DEGREES);

        // ============================ Generate child ============================
        // *** This is the block to experiment with. ***
        Random random = new Random();
        boolean r = random.nextBoolean();
        double magnitude = random.nextDouble() * 0.3 + 0.5;

        childMStick.genNewComponentsMatchStick(parentMStick, compsToMutateInParent, magnitude, 0.5,
                true, 15, compsToMutateInParent);
        // ========================================================================

        return new DeltaResult(childMStick, magnitude);
    }

    /** Holds a generated delta along with the magnitude actually used to produce it. */
    private static class DeltaResult {
        final PruningMatchStick stick;
        final double magnitude;

        DeltaResult(PruningMatchStick stick, double magnitude) {
            this.stick = stick;
            this.magnitude = magnitude;
        }
    }
}
