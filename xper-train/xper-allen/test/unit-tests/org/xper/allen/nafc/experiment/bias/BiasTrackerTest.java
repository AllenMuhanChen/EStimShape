package org.xper.allen.nafc.experiment.bias;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.util.Arrays;
import java.util.List;

import org.junit.Before;
import org.junit.Test;

/**
 * Behavioural spec for {@link BiasTracker}, using a synthetic triplet group (variant V + deltas D1,D2)
 * where each member takes turns being the correct answer. Mirrors the validation simulation.
 */
public class BiasTrackerTest {

    private static final long V = 0L, D1 = 1L, D2 = 2L, VARIANT = 0L;
    private static final List<Long> PRESENT = Arrays.asList(V, D1, D2);
    private static final int N = 3;

    /** A choice policy for the synthetic monkey (no lambdas: Java 7 source level). */
    private interface Policy {
        long choose(int trial, long correct);
    }

    private BiasTracker tracker;

    @Before
    public void setUp() {
        // defaults: lambda .8, sHigh .6, sLow .35, nMin 8, hMin .4, nMinInversion 8
        tracker = new BiasTracker(new BiasTrackerConfig());
    }

    /** Rotate which member is the sample so each is the correct answer on ~1/3 of trials. */
    private long correctForTrial(int t) {
        return t % N;
    }

    private void run(int count, int startT, Policy policy) {
        for (int t = startT; t < startT + count; t++) {
            long correct = correctForTrial(t);
            long chosen = policy.choose(t, correct);
            tracker.update(VARIANT, PRESENT, correct, chosen, N);
        }
    }

    private static final Policy ALWAYS_V = new Policy() {
        public long choose(int trial, long correct) {
            return V;
        }
    };

    private static final Policy DISCRIMINATE = new Policy() {
        public long choose(int trial, long correct) {
            return correct;
        }
    };

    @Test
    public void pureExploitGetsFlagged_butNotBeforeMinSamples() {
        // Always pick V. Over the first 9 trials V is a wrong option only ~6 times (< nMin=8),
        // so the min-sample gate must keep it un-flagged even though the wrong-pick rate is high.
        run(9, 0, ALWAYS_V);
        assertFalse("must not flag before nMin wrong-option sightings", tracker.isBiased(V));

        run(15, 9, ALWAYS_V);
        assertTrue("pure exploit should be flagged once enough evidence accrues", tracker.isBiased(V));
        assertTrue("bias score should be near 1 for a total lock-on", tracker.biasScore(V) > 0.9);
    }

    @Test
    public void discriminatorIsNeverFlagged() {
        run(40, 0, DISCRIMINATE);
        assertFalse(tracker.isBiased(V));
        assertEquals("no bias for a perfect discriminator", 0.0, tracker.biasScore(V), 1e-9);
    }

    @Test
    public void recoversAfterQuittingBias() {
        run(15, 0, ALWAYS_V);
        assertTrue(tracker.isBiased(V));

        run(20, 15, DISCRIMINATE);
        assertFalse("hysteresis + memory should un-flag after discriminating again", tracker.isBiased(V));
    }

    @Test
    public void inversionGuardUnflagsWhenAvoidanceCollapsesHitRate() {
        // Establish the bias.
        run(15, 0, ALWAYS_V);
        assertTrue(tracker.isBiased(V));

        // Now pick V only when it is WRONG (keeps B high, so sLow decay can NOT un-flag) while
        // refusing V when it is the correct answer (collapses the hit-rate H). Only the inversion
        // guard can release this state.
        run(40, 15, new Policy() {
            public long choose(int trial, long correct) {
                return (correct != V) ? V : D1;
            }
        });

        assertFalse("inversion guard should un-flag once avoidance collapses the hit-rate",
                tracker.isBiased(V));
        BiasKeyState s = tracker.get(V);
        assertTrue("hit-rate should have collapsed below hMin", s.ewmaHitWhenCorrect < 0.4);
    }
}
