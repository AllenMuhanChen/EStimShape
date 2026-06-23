package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
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
 * The real createMStick() now anchors ONE shared circle on the PARENT's hypothesized component (the
 * smallest-shift placement that hides it), keyed by (parent_id, comp-set) so every delta of this
 * parent mutating the same comp(s) reuses it; the delta is then generated to fit that fixed circle,
 * retrying morphs and skipping if none fit. So if createMStick() returns without throwing, a delta was
 * found that fits the parent-anchored circle; we then re-confirm its mutated limb is fully inside it.
 *
 * Set {@link #PARENT_ID} to the stim you want to make a delta from.
 */
public class EStimShapeDeltaGAStimTest {

    /** The existing stim to make a delta out of. */
    private static final long PARENT_ID = 1782151044785062L;
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
        // Push the far clip plane way back so a shape with depth can't be z-clipped.
        drawer.setupFrom(generator.getPngMaker(), 1_000_000);
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

        // The delta is generated at the parent's stored RF location, which is off-center; the drawer's
        // field is now sized tightly to the image box (inherited from the generator), so an off-center
        // shape spills outside the frame. Center it for the drawing only (validation above already used
        // the real geometry). centerShape() carries the noise origin along (applyTranslation override),
        // so the comp map's noise stays consistent with the shape.
        child.centerShape();

        drawer.drawMStick(child);
        ThreadUtil.sleep(1000);
        drawer.saveImage(figPath + "/delta_from_db_" + PARENT_ID);
        drawer.drawCompMap(child);
        drawer.saveImage(figPath + "/delta_from_db_" + PARENT_ID+"_compMap");
        ThreadUtil.sleep(1000);

        // Render the parent the same way (centered, same drawer) so the delta can be compared limb-by-
        // limb against it - to tell whether a wrong-looking component came from the parent spec or from
        // the delta generation. Loaded exactly as createMStick() loads it (same properties + GA spec).
        ProceduralMatchStick parent = new ProceduralMatchStick(generator.getNoiseMapper());
        parent.setProperties(delta.sizeDiameterDegrees, delta.textureType, delta.is2d, delta.contrast);
        parent.setStimColor(delta.color);
        parent.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + PARENT_ID + "_spec.xml");
        parent.centerShape();

        drawer.clear();
        drawer.drawMStick(parent);
        ThreadUtil.sleep(1000);
        drawer.saveImage(figPath + "/parent_" + PARENT_ID);
        drawer.drawCompMap(parent);
        drawer.saveImage(figPath + "/parent_" + PARENT_ID + "_compMap");
        ThreadUtil.sleep(1000);

        assertTrue("delta's mutated limb should be (near) fully inside its own circle: " + inside,
                inside >= 0.99);

    }
}
