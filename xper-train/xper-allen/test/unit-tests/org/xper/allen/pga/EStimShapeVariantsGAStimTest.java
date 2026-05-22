package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import java.util.List;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNotEquals;
import static org.xper.allen.pga.RFStrategy.COMPLETELY_INSIDE;

/**
 * End-to-end test of the {@link EStimShapeVariantsGAStim} generation pipeline,
 * focused on verifying that the new "slight mutation of the preserved limb"
 * behavior actually mutates the preserved component without adding or removing
 * limbs.
 *
 * <p>The actual {@code EStimShapeVariantsGAStim} class can't be instantiated
 * directly from a unit test: its parent {@link GAStim} constructor wires up
 * JDBC-backed property managers via Spring's {@code JdbcTemplate}, which
 * requires a live {@link FromDbGABlockGenerator} + database. {@link GAStimTest}
 * pays that price by booting the full Spring context. Here, since there's no
 * mocking framework available, we instead replicate {@code createMStick()}'s
 * matchstick-generation pipeline inline (the same pattern
 * {@code GAMatchStickTest.draw_pruning_mstick} uses for plain pruning sticks)
 * and exercise {@link PruningMatchStick#mutatePreservedComps(double)} on the
 * resulting child the way the real Stim does.
 */
public class EStimShapeVariantsGAStimTest {

    private static final String figPath = "/home/connorlab/Documents/xper-test";

    private static final ReceptiveField COMPLETE_RF = new ReceptiveField() {
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
    public void setUp() {
        drawer = new TestMatchStickDrawer();
        drawer.setup(500, 500);

        noiseMapper = new GaussianNoiseMapper();
        noiseMapper.setWidth(500);
        noiseMapper.setHeight(500);
        noiseMapper.setBackground(0);
        noiseMapper.setDoEnforceHiddenJunction(true);
    }

    /**
     * Replays the pruning-variant branch of {@code EStimShapeVariantsGAStim.createMStick()}:
     * pick comps to preserve, run {@code genPruningMatchStick}, then apply the new
     * slight preserved-comp mutation. Saves images at each stage so the mutation can
     * be eyeballed.
     */
    @Test
    public void test_pruning_variant_then_mutate_preserved_comp() {
        GAMatchStick parent = genParent();
        drawer.drawMStick(parent);
        drawer.saveImage(figPath + "/variant_parent.png");
        ThreadUtil.sleep(500);
        drawer.clear();

        PruningMatchStick child = generatePruningVariant(parent);

        drawer.drawMStick(child);
        drawer.saveImage(figPath + "/variant_child_premutation.png");
        ThreadUtil.sleep(500);
        drawer.drawCompMap(child);
        drawer.saveImage(figPath + "/variant_child_premutation_compmap.png");
        ThreadUtil.sleep(500);
        drawer.clear();

        int nCompsBefore = child.getNComponent();
        List<Integer> preservedBefore = child.getPreservedComps();

        child.mutatePreservedComps(0.15);

        // Slight mutation should not add or remove limbs, and must preserve
        // the identity of which comps are "preserved" so positioning continues to work.
        assertEquals("preserved-comp mutation should not add or remove limbs",
                nCompsBefore, child.getNComponent());
        assertEquals("preserved comp list must be unchanged after mutation",
                preservedBefore, child.getPreservedComps());

        drawer.drawMStick(child);
        drawer.saveImage(figPath + "/variant_child_postmutation.png");
        ThreadUtil.sleep(500);
        drawer.drawCompMap(child);
        drawer.saveImage(figPath + "/variant_child_postmutation_compmap.png");
        ThreadUtil.sleep(500);
    }

    /**
     * Replays the "regrow from preserved component in noise" branch of
     * {@code EStimShapeVariantsGAStim.createMStick()} and applies the slight mutation.
     */
    @Test
    public void test_components_in_noise_variant_then_mutate_preserved_comp() {
        GAMatchStick parent = genParent();
        drawer.drawMStick(parent);
        drawer.saveImage(figPath + "/noise_variant_parent.png");
        ThreadUtil.sleep(500);
        drawer.clear();

        PruningMatchStick child = generateComponentsInNoiseVariant(parent);

        drawer.drawMStick(child);
        drawer.saveImage(figPath + "/noise_variant_child_premutation.png");
        ThreadUtil.sleep(500);
        drawer.clear();

        int nCompsBefore = child.getNComponent();
        List<Integer> preservedBefore = child.getPreservedComps();

        child.mutatePreservedComps(0.15);

        assertEquals(nCompsBefore, child.getNComponent());
        assertEquals(preservedBefore, child.getPreservedComps());

        drawer.drawMStick(child);
        drawer.saveImage(figPath + "/noise_variant_child_postmutation.png");
        ThreadUtil.sleep(500);
    }

    /**
     * When Python's EStimPhaseMagnitudeAssigner returns 0 (the "no slight mutation"
     * outcome), mutatePreservedComps must be a complete no-op.
     */
    @Test
    public void test_zero_magnitude_is_noop() {
        GAMatchStick parent = genParent();
        PruningMatchStick child = generatePruningVariant(parent);

        int nCompsBefore = child.getNComponent();
        List<Integer> preservedBefore = child.getPreservedComps();
        double xBefore = child.getComp()[preservedBefore.get(0)].getMassCenter().x;
        double yBefore = child.getComp()[preservedBefore.get(0)].getMassCenter().y;
        double zBefore = child.getComp()[preservedBefore.get(0)].getMassCenter().z;

        child.mutatePreservedComps(0.0);

        assertEquals(nCompsBefore, child.getNComponent());
        assertEquals(preservedBefore, child.getPreservedComps());
        assertEquals(xBefore, child.getComp()[preservedBefore.get(0)].getMassCenter().x, 1e-9);
        assertEquals(yBefore, child.getComp()[preservedBefore.get(0)].getMassCenter().y, 1e-9);
        assertEquals(zBefore, child.getComp()[preservedBefore.get(0)].getMassCenter().z, 1e-9);
    }

    /**
     * Sanity check that a nonzero magnitude actually moves the preserved comp's
     * geometry. We compare the preserved comp's mAxis arc length before and after;
     * a successful component morph almost always changes the arc length.
     */
    @Test
    public void test_nonzero_magnitude_actually_changes_preserved_comp() {
        GAMatchStick parent = genParent();
        PruningMatchStick child = generatePruningVariant(parent);

        int preservedComp = child.getPreservedComps().get(0);
        double arcLenBefore = child.getComp()[preservedComp].getmAxisInfo().getArcLen();

        child.mutatePreservedComps(0.15);

        double arcLenAfter = child.getComp()[preservedComp].getmAxisInfo().getArcLen();
        assertNotEquals(
                "preserved-comp arc length should change after a magnitude=0.15 mutation",
                arcLenBefore, arcLenAfter, 1e-6);
    }

    /**
     * Visual sweep across mutation magnitudes on the same parent + variant child,
     * so we can confirm low magnitudes give subtle changes and higher magnitudes
     * give larger ones. Ignored by default (image generation only).
     */
    @Ignore
    @Test
    public void fig_examples_of_preserved_comp_mutation_magnitudes() {
        GAMatchStick parent = genParent();
        drawer.drawMStick(parent);
        drawer.saveImage(figPath + "/mag_sweep_parent.png");
        ThreadUtil.sleep(500);
        drawer.clear();

        double[] magnitudes = {0.05, 0.10, 0.15, 0.30};
        for (double magnitude : magnitudes) {
            PruningMatchStick child = generatePruningVariant(parent);
            child.mutatePreservedComps(magnitude);
            drawer.drawMStick(child);
            drawer.saveImage(figPath + "/mag_sweep_mag_" + magnitude + ".png");
            ThreadUtil.sleep(500);
            drawer.clear();
        }
    }

    // --- helpers that replicate the matchstick pipeline in EStimShapeVariantsGAStim ---

    private GAMatchStick genParent() {
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        GAMatchStick parent = new GAMatchStick(COMPLETE_RF, COMPLETELY_INSIDE);
        // bias toward 3-comp parents so there's always a non-preserved comp to morph
        parent.PARAM_nCompDist = new double[]{0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0};
        parent.setProperties(3.0, "SHADE", 1.0);
        parent.setStimColor(color);
        parent.genMatchStickRand();
        return parent;
    }

    private PruningMatchStick generatePruningVariant(GAMatchStick parent) {
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        while (true) {
            try {
                PruningMatchStick child = new PruningMatchStick(noiseMapper);
                child.setRf(COMPLETE_RF);
                child.setMaxTotalAttempts(15);
                child.setProperties(3.0, "SHADE", 1.0);
                child.setStimColor(color);

                List<Integer> compsToPreserve = PruningMatchStick.chooseRandomComponentsToPreserve(1, parent);
                // matches the magnitude range used inside EStimShapeVariantsGAStim.createMStick
                double pruningMagnitude = Math.random() * 0.4 + 0.5;
                child.genPruningMatchStick(parent, pruningMagnitude, compsToPreserve, null);
                return child;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }

    private PruningMatchStick generateComponentsInNoiseVariant(GAMatchStick parent) {
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        while (true) {
            try {
                PruningMatchStick child = new PruningMatchStick(noiseMapper);
                child.setRf(COMPLETE_RF);
                child.setMaxTotalAttempts(15);
                child.setProperties(3.0, "SHADE", 1.0);
                child.setStimColor(color);

                List<Integer> compsToPreserve = PruningMatchStick.chooseRandomComponentsToPreserve(1, parent);
                int nComp = compsToPreserve.size() + 2; // ensure at least one regrown comp
                child.genMatchStickFromComponentsInNoise(parent, compsToPreserve, nComp, true, 15);
                return child;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
}
