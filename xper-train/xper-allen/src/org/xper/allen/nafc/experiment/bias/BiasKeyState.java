package org.xper.allen.nafc.experiment.bias;

/**
 * Persistent per-stimulus bias state tracked by {@link BiasTracker}. One row per stimulus lineage id
 * (a variant id or delta id), grouped under its variant. Fields are public so the DAO can map them
 * straight to/from the {@code bias_controller_state} table and Python can read the same columns.
 *
 * <p>The three EWMAs each answer a different question, updated only on the trials where each is
 * meaningful (a trial where this stimulus is present as a choice):
 * <ul>
 *   <li>{@link #ewmaChose} (A): overall P(chose this | present). Diagnostic reliance signal.</li>
 *   <li>{@link #ewmaChoseWhenWrong} (B): P(chose this | present AND this is a wrong option). The
 *       exploit signal that drives the bias score and the biased state.</li>
 *   <li>{@link #ewmaHitWhenCorrect} (H): P(chose this | present AND this is the correct answer). The
 *       inversion guard &mdash; if it collapses while biased, the animal is avoiding the stimulus.</li>
 * </ul>
 */
public class BiasKeyState {

    /** Stimulus lineage id (variant id or delta id) this state tracks. */
    public long stimId;

    /** Variant id of the group this stimulus belongs to (the variant itself, or its parent variant). */
    public long variantId;

    /** Most recent choice count N on a trial containing this stimulus; sets the chance baseline 1/N. */
    public int numChoices;

    /** A: EWMA of "chose this stimulus", over all trials where it was present. */
    public double ewmaChose;

    /** B: EWMA of "chose this stimulus", over trials where it was present as a wrong option. */
    public double ewmaChoseWhenWrong;

    /** H: EWMA of "chose this stimulus", over trials where it was the correct answer. */
    public double ewmaHitWhenCorrect;

    /** Count of trials where this stimulus was present (any role). */
    public int nPresent;

    /** Count of trials where this stimulus was present as a wrong option. */
    public int nDistractor;

    /** Count of trials where this stimulus was present as the correct answer. */
    public int nCorrectPresent;

    /** Whether this stimulus is currently in the biased state (shaping applies while true). */
    public boolean biased;

    /** Current bias score in [0,1]: 0 = chance, 1 = always picked when it is a wrong option. */
    public double biasScore;

    public BiasKeyState() {
    }

    public BiasKeyState(long stimId, long variantId) {
        this.stimId = stimId;
        this.variantId = variantId;
    }
}
