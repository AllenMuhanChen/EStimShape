package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NoiseCircle;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.util.FileUtil;
import org.xper.util.ThreadUtil;

import java.util.List;

import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

/**
 * Small-scale, DB-backed check of the delta side of the shared-noise-circle work.
 *
 * Instead of guessing size/RF/noise-radius (which hits "vector too long" size rejections), this boots
 * the real GA Spring context and runs the actual {@link EStimShapeDeltaGAStim} on ONE chosen parent
 * stim - so size, RF, position, the noise mapper and the parent spec are all read from the DB exactly
 * as production does (see {@link GAStimTest} for the same context-booting pattern).
 *
 * The real createMStick() now (a) computes the delta's circle with the smallest-shift owner optimizer
 * and (b) rejects the delta unless that same circle also hides the parent's corresponding limb. So if
 * createMStick() returns without throwing, the shared-circle rule held for this parent; we then
 * re-confirm the delta's own limb is fully inside the stored circle.
 *
 * Set {@link #PARENT_ID} to the stim you want to make a delta from.
 */
public class EStimShapeDeltaGAStimTest {

    /** The existing stim to make a delta out of. */
    private static final long PARENT_ID = 1782150336038420L;
    /** Any unused id for the generated delta. */
    private static final long DELTA_STIM_ID = 999999L;
    /** Mutation magnitude (Python passes this in production). */
    private static final double MAGNITUDE = 0.5;

    private static final String figPath = "/home/connorlab/Documents/xper-test";

    private FromDbGABlockGenerator generator;
    private TestMatchStickDrawer drawer;

    @Before
    public void setUp() {
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.ga.config_class"));
        generator = context.getBean(FromDbGABlockGenerator.class);

        drawer = new TestMatchStickDrawer();
        // Inherit the real viewing geometry + image size from the generator so the delta is drawn at
        // the same scale production would render it (rather than hardcoded 500x500 / distance 500).
        drawer.setupFrom(generator.getPngMaker());
    }

    @Test
    public void generate_delta_from_db_stim() {
        EStimShapeDeltaGAStim delta = new EStimShapeDeltaGAStim(DELTA_STIM_ID, generator, PARENT_ID, MAGNITUDE);
        // Reads size / texture / color / contrast for this lineage from the DB, same as writeStim().
        delta.setProperties();

        // The real pipeline: owner smallest-shift optimizer places the circle, and the delta is
        // rejected (MorphException -> retry) unless the circle also hides the parent's limb. If this
        // returns, the shared-circle rule held.
        PruningMatchStick child = delta.createMStick();

        assertNotNull("delta failed to generate", child);
        NoiseCircle circle = delta.noiseCircle;
        assertNotNull("delta produced no noise circle", circle);

        // Re-confirm the delta's own mutated limb (its hypothesized comp, in child numbering) is fully
        // inside the stored circle.
        List<Integer> mutatedInChild = delta.hypothesizedCompData.getHypothesizedComp();
        GaussianNoiseMapper gm = (GaussianNoiseMapper) generator.getNoiseMapper();
        double inside = gm.fractionInside(child, mutatedInChild, circle.getOrigin(), circle.getRadiusMm());

        System.out.println("parent=" + PARENT_ID + " mutated(child)=" + mutatedInChild + " " + circle);
        System.out.println("delta limb inside = " + inside + " ; noiseRadiusMm=" + child.noiseRadiusMm);

        drawer.drawMStick(child);
        ThreadUtil.sleep(500);
        drawer.saveImage(figPath + "/delta_from_db_" + PARENT_ID);
        drawer.drawCompMap(child);
        drawer.saveImage(figPath + "/delta_from_db_" + PARENT_ID+"_compMap");
        ThreadUtil.sleep(1000);
        assertTrue("delta's mutated limb should be (near) fully inside its own circle: " + inside,
                inside >= 0.99);

    }
}
