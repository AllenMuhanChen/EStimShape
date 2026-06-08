package org.xper.allen.pga;

import java.util.List;

/**
 * The hypothesized driving component for a stimulus, tracked across generations.
 *
 * The same physical driver limb is renumbered from one generation to the next, so it is stored
 * in two coordinate systems:
 *  - hypothesizedComp:        the driver comp indexed in THIS stim's own numbering.
 *  - parentHypothesizedComps: the same driver comp indexed in the PARENT's numbering
 *                             (i.e. which of the parent's comps was acted upon to make this stim).
 *
 * A variant preserves the hypothesized comp; a delta mutates it.
 */
public class HypothesizedCompData {
    private final List<Integer> hypothesizedComp;        // driver comp(s), this stim's own numbering
    private final Long parentId;
    private final List<Integer> parentHypothesizedComps; // driver comp(s), parent's numbering

    public HypothesizedCompData(List<Integer> hypothesizedComp, Long parentId, List<Integer> parentHypothesizedComps) {
        this.hypothesizedComp = hypothesizedComp;
        this.parentId = parentId;
        this.parentHypothesizedComps = parentHypothesizedComps;
    }

    public List<Integer> getHypothesizedComp() {
        return hypothesizedComp;
    }

    public Long getParentId() {
        return parentId;
    }

    public List<Integer> getParentHypothesizedComps() {
        return parentHypothesizedComps;
    }
}
