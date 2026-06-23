package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;

import javax.vecmath.Point3d;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

public class EStimShapeDeltaGAStim extends EStimShapeVariantsGAStim{

    private final double magnitude;

    public EStimShapeDeltaGAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude) {
        super(stimId, generator, parentId, magnitude);
        this.magnitude = magnitude;
    }

    @Override
    protected void choosePosition() {
        // A delta anchors itself on the component it preserves (computed in createMStick), so it
        // always uses a preserved-comp-based position regardless of the parent's own positioning.
        // This lets a delta be made from any (non-baseline) high-response parent - a variant, a
        // delta, regime_one, etc. - not just preserved-comp-based variants.
        position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
    }

    /**
     * Which of the parent's components this delta mutates. The hypothesized comp is the fragment
     * being tested: a variant tests it by preserving it, a delta tests it by changing it.
     *
     *  1) Variant parent -> first drive its hypothesized (predicted-driver) comp(s). We mutate the
     *     WHOLE hypothesized comp-set together - including both comps when it's multi-component (e.g.
     *     the parent variant preserved a junction pair). We keep re-testing it until we've spent a
     *     budget of FAILED attempts on that comp-set (num_deltas_per_variant): a failed attempt is a
     *     responded delta that changed exactly those comps and did NOT drop the response past
     *     delta_resp_ratio_threshold. Successes don't consume the budget, so each success effectively
     *     buys another attempt. Once the budget is spent without driving the response down, we fall
     *     through to the same tiered leaf/pair search non-variant parents use.
     *  2) Non-variant parent (delta, growing, regime_one, ...), or a variant whose hypothesized-comp
     *     budget is spent -> systematically search the parent's components, using the parent's
     *     existing delta-children as the record of what's been tried:
     *       a) at least one leaf still has failed-attempt budget left -> pick among those leaves at
     *          random, WEIGHTED by each leaf's best response reduction (1 - bestRatio), so leaves that
     *          dropped the response more are tested more often but every under-budget leaf keeps a
     *          chance (soft weighting, not greedy). A leaf is retried until it has failed
     *          num_deltas_per_variant times; successes don't count. Untested leaves use the mean
     *          observed reduction as a prior, so before any responses come back the pick is uniform.
     *          Weights are recomputed every call from the current sibling responses;
     *       b) every leaf exhausted its budget and SOME passed -> exploit them: pick a passing leaf
     *          weighted by its response reduction;
     *       c) every leaf exhausted its budget and NONE passed -> explore two comps sharing a junction.
     */
    private List<Integer> chooseCompsToMutate(PruningMatchStick parentMStick) {
        int nComp = parentMStick.getNComponent();
        List<SiblingDelta> siblings = readSiblingDeltas();

        // Per-comp budget shared by the hypothesized comp and the leaf search: how many FAILED
        // single-comp attempts we'll tolerate on a comp before giving up on it. A failed attempt is
        // a responded delta that did NOT drop the response past dropThreshold; successes don't count,
        // so each success buys another attempt on that comp.
        int budget = (int) Math.round(readGaVarDouble("num_deltas_per_variant", 1));
        double parentResponse = readResponse(parentId);
        double dropThreshold = readGaVarDouble("delta_resp_ratio_threshold", 0.5);

        // 1) Variant parent: drive its predicted driver until its failed-attempt budget is spent.
        if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ESTIM_VARIANTS) {
            List<Integer> hypothesized = inRange(
                    hypothesizedCompData != null ? hypothesizedCompData.getHypothesizedComp() : null, nComp);
            if (hypothesized.isEmpty()) {
                return Collections.singletonList(parentMStick.chooseRandLeaf());
            }
            // Count failed attempts on the WHOLE hypothesized comp-set (a sibling that changed exactly
            // these comps and didn't drop the response). The hypothesized comp may be multi-component
            // (e.g. the parent variant preserved a junction pair); we test it as a unit.
            Set<Integer> hypothesizedSet = new HashSet<>(hypothesized);
            int failedOnHypothesized = 0;
            for (SiblingDelta s : siblings) {
                if (isFailedDelta(s, parentResponse, dropThreshold)
                        && new HashSet<>(s.changedComps).equals(hypothesizedSet)) {
                    failedOnHypothesized++;
                }
            }
            if (failedOnHypothesized < budget) {
                // Mutate the hypothesized comp(s) - all of them together when it's multi-component.
                return new ArrayList<>(hypothesized);
            }
            // Budget spent without dropping the response: escalate to the tiered search below. The
            // hypothesized comp is already a budgeted leaf, so the search naturally explores the rest.
        }

        // 2) Tiered search over the parent's leaves.
        List<Integer> leaves = leavesOf(parentMStick);
        if (leaves.isEmpty()) {
            for (int i = 1; i <= nComp; i++) leaves.add(i);
        }

        // Best (lowest) response-reduction ratio per leaf, from RESPONDED siblings. Lower ratio =
        // bigger response drop. Recomputed every call, so weights update as more deltas come back.
        Map<Integer, Double> bestRatio = new HashMap<>();
        if (parentResponse > 0) {
            for (SiblingDelta s : siblings) {
                if (s.changedComps.size() == 1 && s.response != null) {
                    int leaf = s.changedComps.get(0);
                    double ratio = s.response / parentResponse;
                    Double prev = bestRatio.get(leaf);
                    if (prev == null || ratio < prev) bestRatio.put(leaf, ratio);
                }
            }
        }

        // Failed single-comp attempts per leaf (successes don't count toward the budget).
        Map<Integer, Integer> failedPerLeaf = new HashMap<>();
        for (SiblingDelta s : siblings) {
            if (isFailedSingleComp(s, parentResponse, dropThreshold)) {
                int leaf = s.changedComps.get(0);
                failedPerLeaf.put(leaf, failedPerLeaf.getOrDefault(leaf, 0) + 1);
            }
        }

        // (a) Among the leaves that still have failure budget left (same budget as the hypothesized
        //     comp), pick one weighted by its response reduction (1 - bestRatio): bigger drops are
        //     more likely, but every under-budget leaf keeps a chance - it's soft weighting, not
        //     greedy. Leaves with no responded data yet use the mean observed reduction as a neutral
        //     prior, so before any responses come back the pick is uniform.
        List<Integer> eligible = new ArrayList<>();
        for (Integer leaf : leaves) {
            if (failedPerLeaf.getOrDefault(leaf, 0) < budget) eligible.add(leaf);
        }
        if (!eligible.isEmpty()) {
            return Collections.singletonList(weightedPickByReduction(eligible, bestRatio));
        }

        // (b) Every leaf exhausted its failure budget. If some leaf ever dropped the response past
        //     the threshold, exploit the best of them; otherwise explore two comps sharing a junction.
        List<Integer> passing = new ArrayList<>();
        for (Map.Entry<Integer, Double> e : bestRatio.entrySet()) {
            if (e.getValue() < dropThreshold) passing.add(e.getKey());
        }
        if (passing.isEmpty()) {
            if (nComp >= 3) {
                List<Integer> pair = inRange(
                        PruningMatchStick.chooseRandomComponentsToPreserve(2, parentMStick), nComp);
                if (pair.size() == 2) return pair;
            }
            return Collections.singletonList(parentMStick.chooseRandLeaf());
        }
        return Collections.singletonList(weightedPickByReduction(passing, bestRatio));
    }

    /**
     * Whether a sibling delta counts as FAILED: it has come back with a response and that response
     * did NOT drop past the ratio threshold relative to the parent. In-flight (null response) deltas
     * are not failures. Says nothing about how many comps it changed.
     */
    private boolean isFailedDelta(SiblingDelta s, double parentResponse, double dropThreshold) {
        return s.response != null
                && parentResponse > 0
                && s.response / parentResponse >= dropThreshold;
    }

    /** A FAILED delta (see {@link #isFailedDelta}) that changed exactly one comp. */
    private boolean isFailedSingleComp(SiblingDelta s, double parentResponse, double dropThreshold) {
        return s.changedComps.size() == 1 && isFailedDelta(s, parentResponse, dropThreshold);
    }

    /**
     * Pick one candidate leaf with probability proportional to its response reduction (1 - bestRatio):
     * leaves that dropped the response more are favored, but every candidate keeps a non-zero chance.
     * A candidate with no responded data in {@code bestRatio} uses the mean observed reduction as a
     * neutral prior (and when nothing has responded at all, every candidate weighs the same, so the
     * pick is uniform). Always returns one of {@code candidates}.
     */
    private Integer weightedPickByReduction(List<Integer> candidates, Map<Integer, Double> bestRatio) {
        // Mean observed reduction, used as the prior for candidates that have no data yet.
        double sumReduction = 0;
        for (Double ratio : bestRatio.values()) sumReduction += Math.max(0.0, 1.0 - ratio);
        double priorReduction = bestRatio.isEmpty() ? 1.0 : sumReduction / bestRatio.size();

        double total = 0;
        for (Integer leaf : candidates) total += reductionWeight(leaf, bestRatio, priorReduction);
        double r = new Random().nextDouble() * total;
        double cum = 0;
        for (Integer leaf : candidates) {
            cum += reductionWeight(leaf, bestRatio, priorReduction);
            if (r <= cum) return leaf;
        }
        return candidates.get(candidates.size() - 1);
    }

    /** Sampling weight for a leaf: its response reduction (1 - bestRatio), or the prior if untested. */
    private double reductionWeight(Integer leaf, Map<Integer, Double> bestRatio, double priorReduction) {
        Double ratio = bestRatio.get(leaf);
        double reduction = (ratio != null) ? (1.0 - ratio) : priorReduction;
        return Math.max(1e-6, reduction);
    }

    /** A delta child of this delta's parent: the parent-numbered comp(s) it changed + its response (nullable). */
    private static class SiblingDelta {
        final List<Integer> changedComps;
        final Double response;
        SiblingDelta(List<Integer> changedComps, Double response) {
            this.changedComps = changedComps;
            this.response = response;
        }
    }

    /**
     * Every delta child of this delta's parent, with the comp it changed (in the parent's numbering,
     * from its HypothesizedComp.parent_hypothesized_comps) and its response (null = not yet
     * collected). This delta's own just-written StimGaInfo row may be included; it has no comp row
     * and a null response yet, so it contributes nothing.
     */
    private List<SiblingDelta> readSiblingDeltas() {
        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        // First collect (stim_id, response); look up the changed comp afterwards so we don't run a
        // nested query inside the RowMapper while this ResultSet is open.
        List idAndResponse = jt.query(
                "SELECT stim_id, response FROM StimGaInfo WHERE parent_id = ? AND stim_type = ?",
                new Object[]{parentId, StimType.REGIME_ESTIM_DELTA.getValue()},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        long siblingId = rs.getLong("stim_id");
                        double resp = rs.getDouble("response");
                        Double response = rs.wasNull() ? null : resp;
                        return new Object[]{siblingId, response};
                    }
                });
        List<SiblingDelta> out = new ArrayList<>();
        for (Object o : idAndResponse) {
            Object[] row = (Object[]) o;
            Long siblingId = (Long) row[0];
            Double response = (Double) row[1];
            List<Integer> changed = Collections.emptyList();
            if (hypothesizedCompManager.hasProperty(siblingId)) {
                List<Integer> c = hypothesizedCompManager.readProperty(siblingId).getParentHypothesizedComps();
                if (c != null) changed = c;
            }
            out.add(new SiblingDelta(changed, response));
        }
        return out;
    }

    @Override
    protected PruningMatchStick createMStick() {
        MStickPosition parentPosition = positionManager.readProperty(parentId);
        PruningMatchStick parentMStick = new PruningMatchStick(parentPosition.getPosition(), generator.getNoiseMapper());
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        List<Integer> compsToMutateInParent = chooseCompsToMutate(parentMStick);



        List<Integer> compsToPreserveInParent = new ArrayList<>();
        for (int i=1; i<=parentMStick.getNComponent(); i++){
            if (!compsToMutateInParent.contains(i)){
                compsToPreserveInParent.add(i);
            }
        }

        PruningMatchStick childMStick;
        if (position.getPosition() == null){
            Point3d toPreserveCompLocation = parentMStick.getComp()[compsToPreserveInParent.get(0)].getMassCenter();
            childMStick = new PruningMatchStick(toPreserveCompLocation, generator.getNoiseMapper());
            childMStick.setPreservedComps(compsToPreserveInParent);
            childMStick.setToPreserveInParent(compsToPreserveInParent);
        } else {
            throw new IllegalArgumentException("Delta parent's position should be preserved comp based");
        }


        childMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        childMStick.setStimColor(color);
        childMStick.setMaxDiameterDegrees(generator.getImageDimensionsDegrees());




        // Generate child
        // Magnitude is decided by Python (passed in as a parameter); discreteness is still
        // chosen randomly here (Python ignores it for now).
        Random random = new Random();
        double discreteness = random.nextDouble();
        childMStick.genNewComponentsMatchStick(parentMStick, compsToMutateInParent, magnitude, discreteness,
                true, 15, compsToMutateInParent);

        // Save data for this stimulus. Position still anchors on a PRESERVED comp (the changed one
        // has new geometry and would drag the shape around).
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
        position.setPosition(childMStick.getMassCenterForComponent(compsToPreserveInNextChild.get(0)));
        position.setTargetComp(compsToPreserveInNextChild.get(0));

        // The hypothesized comp is the fragment THIS DELTA IS TESTING - the comp it CHANGED (a
        // variant tests its hypothesized comp by preserving it; a delta tests it by changing it).
        // Stored in the delta's own numbering (the complement of its preserved comps), with
        // parent_hypothesized_comps = the same tested comp in the parent's numbering (what NAFC
        // reads back). A delta chained onto this one excludes hypothesized_comp from its
        // candidates: if this delta stays high-response, changing this comp didn't matter.
        List<Integer> changedInChild = new ArrayList<>();
        for (int i = 1; i <= childMStick.getNComponent(); i++) {
            if (!compsToPreserveInNextChild.contains(i)) {
                changedInChild.add(i);
            }
        }
        hypothesizedCompData = new HypothesizedCompData(
                changedInChild,
                parentId,
                compsToMutateInParent
        );

        // This delta owns the shared noise circle (computed during generation, tracked through
        // positioning by the applyTranslation override). Validating that it also hides the parent's
        // corresponding limb - and switching the owner generation to the smallest-shift optimizer -
        // is wired in a later step.
        noiseCircle = captureNoiseCircle(childMStick);

        return childMStick;
    }
}
