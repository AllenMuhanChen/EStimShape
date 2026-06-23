package org.xper.allen.pga;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.noisy.GaussianNoiseMapper;
import org.xper.allen.drawing.composition.noisy.NoiseCircle;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.drawing.ga.TestMatchStickDrawer;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

import static org.junit.Assert.assertTrue;
import static org.xper.allen.pga.RFStrategy.COMPLETELY_INSIDE;

/**
 * Small-scale, DB-free check of the delta side of the shared-noise-circle work.
 *
 * The real {@link EStimShapeDeltaGAStim} can't be instantiated from a unit test - its {@link GAStim}
 * constructor wires JDBC-backed property managers that need Spring + a live DB (see
 * {@link EStimShapeVariantsGAStimTest} for the same constraint). So this replicates the matchstick
 * part of {@code EStimShapeDeltaGAStim.createMStick()} inline, with the owner smallest-shift
 * optimizer turned on the same way {@code GAStim.beginOwnerCircleOptimization()} does, and asserts
 * the rule that gates whether a delta can be made:
 *
 *   the delta's single noise circle must hide BOTH the delta's mutated limb AND the parent's
 *   corresponding limb.
 *
 * It also exercises the {@code applyTranslation} frame fix, since the delta is positioned (its
 * preserved comp aligned to the parent's) AFTER its noise circle is computed.
 *
 * To run against live GA data, point {@link #PARENT_SPEC_PATH} at a real {@code *_spec.xml}; leave it
 * null to use a freshly generated synthetic parent. {@link #NOISE_RADIUS_MM} and {@link #SIZE} are
 * the knobs to match your GA's actual values if the asserts fail for size reasons.
 */
public class EStimShapeDeltaGAStimTest {

    private static final String figPath = "/home/connorlab/Documents/xper-test";

    /** Set to a real "<id>_spec.xml" to test against live GA data; null => synthetic parent. */
    private static final String PARENT_SPEC_PATH = null;

    private static final double SIZE = 3.0;                 // maxSizeDiameterDegrees
    private static final double MAX_DIAMETER_DEGREES = 15;  // PNG box; must fit the shape
    private static final double NOISE_RADIUS_MM = 8.0;      // bigger than a limb, smaller than the shape

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
        // Owner mode: smallest shift that hides the WHOLE limb (mirrors GAStim.beginOwnerCircleOptimization).
        noiseMapper.setOptimizeShiftToHideComps(true);
        noiseMapper.setTargetInsideFraction(1.0);
        noiseMapper.setPercentRequiredInside(1.0);
    }

    @Test
    public void delta_circle_hides_both_delta_and_parent_limb() {
        ProceduralMatchStick parent = loadOrGenParent();

        // Mutate one comp, preserve the rest (the delta positions on a preserved comp).
        List<Integer> compsToMutate = Collections.singletonList(1);
        List<Integer> compsToPreserve = new ArrayList<>();
        for (int i = 1; i <= parent.getNComponent(); i++) {
            if (!compsToMutate.contains(i)) {
                compsToPreserve.add(i);
            }
        }
        assertTrue("parent must have >= 2 comps to make a delta", !compsToPreserve.isEmpty());

        PruningMatchStick delta = generateDelta(parent, compsToMutate, compsToPreserve);

        // The circle the delta owns (origin tracked through positioning by the applyTranslation fix).
        NoiseCircle circle = new NoiseCircle(delta.getNoiseOrigin(), delta.noiseRadiusMm);

        double deltaInside = noiseMapper.fractionInside(delta, compsToMutate, circle.getOrigin(), circle.getRadiusMm());
        // The parent's corresponding limb is compsToMutate in the PARENT's numbering. Here parent and
        // child share comp numbering (delta mutates comp 1, parent's comp 1 is the same limb), and the
        // delta was positioned to the parent's preserved comp, so they're in a common frame.
        double parentInside = noiseMapper.fractionInside(parent, compsToMutate, circle.getOrigin(), circle.getRadiusMm());

        System.out.println("shared " + circle);
        System.out.println("delta limb inside  = " + deltaInside);
        System.out.println("parent limb inside = " + parentInside);

        drawer.drawMStick(delta);
        drawer.saveImage(figPath + "/delta_shared_circle.png");
        ThreadUtil.sleep(300);

        assertTrue("delta's mutated limb must be fully hidden by its own circle (" + deltaInside + ")",
                deltaInside >= 1.0 - 1e-9);
        assertTrue("the same circle must also hide the parent's corresponding limb (" + parentInside + ")",
                parentInside >= 1.0 - 1e-9);
    }

    /**
     * The delta pipeline needs a {@link ProceduralMatchStick} parent (genNewComponentsMatchStick and
     * fractionInside both require one), so we load the parent into one - from a real spec file when
     * PARENT_SPEC_PATH is set (production's path), or from a freshly generated synthetic seed otherwise.
     */
    private ProceduralMatchStick loadOrGenParent() {
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        ProceduralMatchStick parent = new ProceduralMatchStick(noiseMapper);
        parent.setRf(COMPLETE_RF);
        parent.setProperties(SIZE, "SHADE", 1.0);
        parent.setStimColor(color);
        if (PARENT_SPEC_PATH != null) {
            parent.genMatchStickFromFile(PARENT_SPEC_PATH);
        } else {
            // Two comps: 1 mutated + 1 preserved is the fast, reliable case (see EStimShapeVariantsGAStimTest).
            GAMatchStick seed = new GAMatchStick(COMPLETE_RF, COMPLETELY_INSIDE);
            seed.PARAM_nCompDist = new double[]{0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0};
            seed.setProperties(SIZE, "SHADE", 1.0);
            seed.setStimColor(color);
            seed.genMatchStickRand();
            AllenMStickSpec spec = new AllenMStickSpec();
            spec.setMStickInfo(seed, false);
            parent.genMatchStickFromShapeSpec(spec, new double[]{0, 0, 0});
        }
        return parent;
    }

    /**
     * Replicates EStimShapeDeltaGAStim.createMStick()'s matchstick pipeline: position the child on a
     * preserved comp, then regrow/mutate the chosen comp with the owner optimizer active. Retries a
     * few times like writeStim() does.
     */
    private PruningMatchStick generateDelta(ProceduralMatchStick parent, List<Integer> compsToMutate, List<Integer> compsToPreserve) {
        RGBColor color = new RGBColor(1.0, 0.0, 0.0);
        int attempts = 0;
        while (attempts++ < 10) {
            try {
                Point3d toPreserveLoc = parent.getComp()[compsToPreserve.get(0)].getMassCenter();
                PruningMatchStick delta = new PruningMatchStick(toPreserveLoc, noiseMapper);
                delta.setPreservedComps(compsToPreserve);
                delta.setToPreserveInParent(compsToPreserve);
                delta.setRf(COMPLETE_RF);
                delta.setMaxTotalAttempts(5);
                delta.setProperties(SIZE, "SHADE", 1.0);
                delta.setStimColor(color);
                delta.setMaxDiameterDegrees(MAX_DIAMETER_DEGREES);
                delta.noiseRadiusMm = NOISE_RADIUS_MM;

                double discreteness = new Random().nextDouble();
                delta.genNewComponentsMatchStick(parent, compsToMutate, 0.5, discreteness,
                        true, 15, compsToMutate);
                return delta;
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        throw new RuntimeException("Could not generate delta in " + attempts + " attempts");
    }
}
