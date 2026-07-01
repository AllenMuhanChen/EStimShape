package org.xper.allen.nafc.experiment.bias;

import java.util.Collections;
import java.util.List;

/**
 * The lineage (variant/delta) view of one completed NAFC trial, as resolved by {@link LineageResolver}
 * from the trial's choices. Everything the {@link BiasTracker} needs for one update, plus a
 * {@link #resolvable} flag: when the trial's lineage structure can't be reconstructed (missing
 * BaseMStickId/IncludedDeltas, non-variant/delta trial, etc.) the controller skips it rather than
 * feeding the tracker garbage.
 */
public class TrialLineage {

    /** Whether the lineage structure was reconstructed. If false, all other fields are unset. */
    public final boolean resolvable;

    /** Variant id of this trial's group (the variant itself, or the parent variant of a delta sample). */
    public final long variantId;

    /** Lineage id of the correct (matching) choice — equal to the sample's lineage id. */
    public final long correctId;

    /**
     * Lineage id the animal actually picked, or {@code null} if the pick was not a plain lineage
     * member (rand/removed/procedural/textureFoil). A null chosen id still updates the tracker: it
     * simply means none of the present lineage members were chosen this trial.
     */
    public final Long chosenId;

    /** Lineage ids of every variant/delta member shown as a choice this trial (sample + lineage distractors). */
    public final List<Long> presentIds;

    /** Number of choices N shown this trial (sets the chance baseline 1/N). */
    public final int numChoices;

    private TrialLineage(boolean resolvable, long variantId, long correctId, Long chosenId,
                         List<Long> presentIds, int numChoices) {
        this.resolvable = resolvable;
        this.variantId = variantId;
        this.correctId = correctId;
        this.chosenId = chosenId;
        this.presentIds = presentIds;
        this.numChoices = numChoices;
    }

    public static TrialLineage unresolved() {
        return new TrialLineage(false, 0L, 0L, null, Collections.<Long>emptyList(), 0);
    }

    public static TrialLineage resolved(long variantId, long correctId, Long chosenId,
                                        List<Long> presentIds, int numChoices) {
        return new TrialLineage(true, variantId, correctId, chosenId, presentIds, numChoices);
    }
}
