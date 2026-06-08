package org.xper.allen.drawing.ga;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import java.io.File;
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
        parentMStick.setProperties(SIZE_DIAMETER_DEGREES, TEXTURE_TYPE, IS_2D, CONTRAST);
        parentMStick.setStimColor(COLOR);
        parentMStick.genMatchStickFromFile(PARENT_SPEC_PATH);

        // Save the original for reference (shape + component map so it's easy to pick "special limbs").
        drawer.draw(parentMStick);
        ThreadUtil.sleep(500);
        drawer.saveImage(OUTPUT_DIR + "/original");
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
            PruningMatchStick childMStick = null;
            while (childMStick == null) {
                try {
                    childMStick = generateDelta(parentMStick, compsToMutateInParent, compsToPreserveInParent);
                } catch (Exception e) {
                    System.out.println("Delta " + deltaIdx + " attempt failed, retrying: " + e.getMessage());
                }
            }

            drawer.draw(childMStick);
            ThreadUtil.sleep(500);
            drawer.saveImage(OUTPUT_DIR + "/delta_" + deltaIdx);
            ThreadUtil.sleep(250);
            drawer.clear();
            System.out.println("Saved delta " + deltaIdx);
        }

        System.out.println("Done. Wrote original + " + NUM_DELTAS + " deltas to " + OUTPUT_DIR);
    }

    /**
     * Reproduces the child-generation logic from EStimShapeVariantsDeltaStim.createMStick().
     *
     * THIS is the part you're testing — tweak the "Generate child" block below to make deltas
     * more likely to be geometrically distinct, then port the winner back into the real class.
     */
    private PruningMatchStick generateDelta(PruningMatchStick parentMStick,
                                            List<Integer> compsToMutateInParent,
                                            List<Integer> compsToPreserveInParent) {
        // Position the child so its first preserved comp lands where it was in the parent.
        Point3d toPreserveCompLocation = parentMStick.getComp()[compsToPreserveInParent.get(0)].getMassCenter();
        PruningMatchStick childMStick = new PruningMatchStick(toPreserveCompLocation, noiseMapper);
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

        return childMStick;
    }
}
