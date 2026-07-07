package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.stick.JuncPt_struct;
import org.xper.drawing.stick.stickMath_lib;

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

public class EStimShapeVariantsGAStim extends GAStim<PruningMatchStick, AllenMStickData>{
    private static final Random random = new Random();
    private final double magnitude;

    public EStimShapeVariantsGAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude) {
        super(stimId, generator, parentId, "PARENT", true);
        this.magnitude = magnitude;
    }

    @Override
    protected void choosePosition() {
        MStickPosition parentLocation = positionManager.readProperty(parentId);
        // could be another variant or a growing stick or zooming or whatever...
        if (parentLocation.positioningStrategy != PositioningStrategy.PRESERVED_COMP_BASED){
            position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
        } else{
            Point3d oldPosition = parentLocation.getPosition();
            position = new MStickPosition(parentLocation.getPositioningStrategy(), oldPosition);        }
    }

    @Override
    protected void chooseTextureType() {
        super.chooseTextureType();
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        sizeDiameterDegrees = sizeManager.readProperty(parentId);
    }



    @Override
    protected PruningMatchStick createMStick() {
        GAMatchStick parentMStick = new GAMatchStick(generator.getReceptiveField(), null);
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        PruningMatchStick childMStick;
        if (position.getPosition() == null){
            childMStick = new PruningMatchStick(generator.getNoiseMapper());
        } else {
            childMStick = new PruningMatchStick(position.getPosition(), generator.getNoiseMapper());
        }


        childMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        childMStick.setStimColor(color);
        childMStick.setMaxDiameterDegrees(generator.getImageDimensionsDegrees());
        childMStick.setRf(generator.getReceptiveField());
        // Read or choose components to preserve from parent

//        List<Integer> compsToPreserveInParent = hypothesizedCompData.getHypothesizedComp();
        List<Integer> compsToPreserveInParent;
        if (shouldChooseRandomCompsToTest()) {
            // Sibling-aware search over which comp(s) to preserve: leaves first, then junction pairs,
            // exploiting comps that held the response up (see chooseCompsToPreserve).
            compsToPreserveInParent = chooseCompsToPreserve(parentMStick);
        } else {
            // shouldPreserveRandomComps()==false guarantees a non-empty list via parentHasHypothesizedComp.
            // Variant-of-a-variant: preserve the same comp the parent preserved (its hypothesized comp).
            compsToPreserveInParent = hypothesizedCompManager.readHypothesizedCompOrNull(parentId);
        }

        // Generate child. Owner mode: place the noise circle with the smallest-shift search that hides
        // the whole preserved limb. Restore the shared mapper afterward (used by NAFC/other paths too).
        Random random = new Random();
        boolean r = random.nextBoolean();

        NoiseOptState prevNoiseOpt = beginOwnerCircleOptimization();
        try {
            if (r) {
                double pruningMagnitude = random.nextDouble() * 0.5 + 0.3;
                childMStick.genPruningMatchStick(parentMStick, pruningMagnitude, compsToPreserveInParent, null);
            }
            else {
                int nComp = 0;
                while (nComp <= compsToPreserveInParent.size()) {
                    nComp = stickMath_lib.pickFromProbDist(PruningMatchStick.PARAM_nCompDist);
                }
                childMStick.genMatchStickFromComponentsInNoise(parentMStick, compsToPreserveInParent, nComp,
                        true, 15);
            }

            // Slightly mutate the preserved limb if Python assigned a nonzero magnitude.
            // Never adds or removes limbs - only morphs the preserved comp(s) in place.
            childMStick.mutatePreservedComps(magnitude);
        } finally {
            endOwnerCircleOptimization(prevNoiseOpt);
        }


        // Save data for this stimulus
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
        position.setPosition(childMStick.getMassCenterForComponent(compsToPreserveInNextChild.get(0)));
        position.setTargetComp(compsToPreserveInNextChild.get(0));
        hypothesizedCompData = new HypothesizedCompData(
                compsToPreserveInNextChild,
                parentId,
                compsToPreserveInParent
        );
//        hypothesizedCompManager.writeProperty(stimId, childData); //shouldn't have to do this now, we put this in GAStim

        // This variant owns its noise circle (computed during generation, tracked through positioning).
        noiseCircle = captureNoiseCircle(childMStick);

        return childMStick;
    }

    /**
     * We should keep the preserved comp the same if a parent-child pair  can identify the driving component by looking at responses of the parent-child.
     * So if we make a variant of a normal stimulus, and we preserve comp 1 and change the rest, then if in the child the stimulus still fires high,
     * this is evidence that comp 1 is the driving component.
     *
     * Valid such comparisons are:
     * 1) VARIANTS with randomly chosen preserved comps
     * 2) VARIANTS OF variants where we preserve the same comp as the parent (because that preserved comp is what the parent preserved, so if we preserve that same comp in the child, it's likely to still be the driving comp)
     * 3) low response DELTAS of high response variants, where we change the driving component and that drives the response down. We can be pretty confident in this case that the component we changed is the driving component, because if it weren't, changing it wouldn't have driven the response down.
     * 4) high response DELTAS of low response variants, where we change the driving component and that drives the response up. We can be pretty confident in this case that the component we changed is the driving component, because if it weren't, changing it wouldn't have driven the response up.
     *
     *  So... if we have preservation history but the stimulus was mutated since the last time we preserved comps, then we should probably assign new comps to preserve randomly, because we don't know which component is driving the response anymore. This is basically saying that if we have a parent-child pair where the parent had preserved comps but the child is a delta that probably changed the preserved comp,
     *  then we shouldn't trust the preserved comp history and should assign new comps to preserve randomly for the child.
     *
     * A caveat with all of this is that these are only really valid at high responses, because we could always be changing the object centered position
     * and that causes the responses to change, but this is more likely earlier on in the GA.
     *
     *
     * @return
     */
    protected boolean shouldChooseRandomCompsToTest() {
        // no preservation history, so preserve random comps.
        if (!parentHasHypothesizedComp()) {
            return true;
        }

        //has preservation history
        if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ONE){
            return true; // if it's regime one, we probably have changed the preserved comp and other comps, so we don't know what's driving response, need to re-test.
        } else if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ESTIM_DELTA){
            Random r  = new Random();
            return r.nextBoolean(); // if it's a high response delta, then we might have changed the wrong component, or we have a new component that's driving even better.
        } else if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ESTIM_VARIANTS){
            return false; // if it's a variant that's high response, then we know which comp we preserved in the parent, and we know that the preserved comp is still driving response in the child, so we should preserve that same comp in the child of the variant.
        }else{ //in doubt, assign new comps to preserve randomly, because we don't know what's driving the response anymore.
            return true;
        }

    }

    protected boolean parentHasHypothesizedComp() {
        // Require a non-empty comp list, not just a row: rows with an empty hypothesized_comp
        // exist (e.g. pre-populated rows for deltas that were never generated) and must route to
        // the random-comps path instead of an empty preserved list.
        return hypothesizedCompManager.readHypothesizedCompOrNull(parentId) != null;
    }

    /**
     * Choose which of the parent's comp(s) to preserve when testing fresh comps (i.e. not simply
     * inheriting a variant-parent's hypothesized comp). Mirrors the delta search, but for PRESERVING
     * comps, and leans exploit:
     *   - EXPLOIT: if a sibling variant preserved some comp(s) and kept at least
     *     variant_parent_response_threshold of the parent's response, preserve those same comp(s) -
     *     the highest-response sibling wins. A preserved comp that holds the response up is evidence
     *     it drives the response.
     *   - EXPLORE: otherwise, test leaves first - sample among the leaves that still have budget,
     *     weighted by their best preserved response (higher response preserved = more likely). Untested
     *     leaves use the parent's response as a neutral-optimistic prior, so they're tried before ones
     *     already seen to drop the response. Each leaf carries a budget of FAILED-to-hold attempts
     *     (num_variants_per_comp): a failed attempt is a responded variant that preserved exactly that
     *     leaf and did NOT keep the response at/above variant_parent_response_threshold. A hold is
     *     caught by the EXPLOIT branch above, so it never reaches here; successes don't spend budget,
     *     so each success effectively buys another attempt. Only once EVERY leaf has spent its
     *     failed-attempt budget do we escalate to two comps sharing a junction (also sampled
     *     probabilistically the same way). Counting only responded failures guarantees single-component
     *     exploration is finished - the required reps are in hand - before any multi-component set is
     *     attempted, and stops same-generation siblings (generated before any responses are collected)
     *     from escalating to a pair in the very same generation.
     */
    protected List<Integer> chooseCompsToPreserve(GAMatchStick parentMStick) {
        int nComp = parentMStick.getNComponent();
        List<SiblingVariant> siblings = readSiblingVariants();
        double parentResp = readResponse(parentId);
        // A sibling "preserved" the response if it kept at least this fraction of the parent's
        // response (the same variant_parent_response_threshold used to gate variant parents).
        double preserveThreshold = readGaVarDouble("variant_parent_response_threshold", 0.8);

        // EXPLOIT: highest-response sibling that held the response at/above the threshold.
        SiblingVariant best = null;
        for (SiblingVariant s : siblings) {
            if (s.response != null && parentResp > 0 && s.response / parentResp >= preserveThreshold
                    && !s.preservedComps.isEmpty()) {
                if (best == null || s.response > best.response) best = s;
            }
        }
        if (best != null) {
            List<Integer> comps = inRange(best.preservedComps, nComp);
            if (!comps.isEmpty()) return comps;
        }

        // EXPLORE: best (max) preserved response per comp-set (for weighting), plus a count of
        // FAILED-to-hold attempts per comp-set. Keyed by the sorted comp list. Only responded
        // siblings count; a hold (>= threshold) would have been returned by EXPLOIT above, so what
        // reaches here are failures that each spend one unit of that leaf's budget.
        int budget = Math.max(1, (int) Math.round(readGaVarDouble("num_variants_per_comp", 1)));
        Map<List<Integer>, Double> bestPreservedResp = new HashMap<>();
        Map<List<Integer>, Integer> failedReps = new HashMap<>();
        for (SiblingVariant s : siblings) {
            if (s.response == null) continue; // not measured yet -> spends no budget
            List<Integer> key = inRange(s.preservedComps, nComp);
            if (key.isEmpty()) continue;
            Collections.sort(key);
            Double prev = bestPreservedResp.get(key);
            if (prev == null || s.response > prev) bestPreservedResp.put(key, s.response);
            boolean held = parentResp > 0 && s.response / parentResp >= preserveThreshold;
            if (!held) failedReps.merge(key, 1, Integer::sum);
        }

        List<Integer> leaves = leavesOf(parentMStick);
        if (leaves.isEmpty()) {
            for (int i = 1; i <= nComp; i++) leaves.add(i);
        }

        // Leaves that haven't yet failed to hold `budget` times keep getting retested first; only
        // once every leaf has spent its failed-attempt budget do we escalate to junction pairs. Both
        // tiers are sampled probabilistically (weighted by best preserved response; comp-sets with no
        // response yet use the parent's response as a neutral-optimistic prior).
        List<List<Integer>> underBudgetLeaves = new ArrayList<>();
        for (Integer leaf : leaves) {
            if (failedReps.getOrDefault(Collections.singletonList(leaf), 0) < budget) {
                underBudgetLeaves.add(Collections.singletonList(leaf));
            }
        }

        List<List<Integer>> candidates = new ArrayList<>();
        if (!underBudgetLeaves.isEmpty()) {
            candidates = underBudgetLeaves; // single-component exploration not finished yet
        } else if (nComp >= 3) {
            candidates = junctionPairsOf(parentMStick, nComp); // every leaf spent its budget -> pairs
        }
        if (candidates.isEmpty()) {
            for (Integer leaf : leaves) candidates.add(Collections.singletonList(leaf));
        }
        return weightedSampleByPreservedResp(candidates, bestPreservedResp, parentResp);
    }

    /** Pick a comp-set with probability proportional to its best preserved response (untried -> prior). */
    private List<Integer> weightedSampleByPreservedResp(List<List<Integer>> candidates,
                                                        Map<List<Integer>, Double> bestPreservedResp, double prior) {
        double total = 0;
        for (List<Integer> comps : candidates) total += preservedWeight(comps, bestPreservedResp, prior);
        double r = random.nextDouble() * total;
        double cum = 0;
        for (List<Integer> comps : candidates) {
            cum += preservedWeight(comps, bestPreservedResp, prior);
            if (r <= cum) return comps;
        }
        return candidates.get(candidates.size() - 1);
    }

    /** Sampling weight for a comp-set: its best preserved response, or the prior if not yet tried. */
    private double preservedWeight(List<Integer> comps, Map<List<Integer>, Double> bestPreservedResp, double prior) {
        Double resp = bestPreservedResp.get(comps);
        return Math.max(1e-6, resp != null ? resp : prior);
    }

    /** All distinct junction-sharing comp pairs of the parent, each as a sorted in-range pair. */
    private List<List<Integer>> junctionPairsOf(GAMatchStick parentMStick, int nComp) {
        List<List<Integer>> pairs = new ArrayList<>();
        Set<List<Integer>> seen = new HashSet<>();
        JuncPt_struct[] juncs = parentMStick.getJuncPt();
        if (juncs == null) return pairs;
        for (JuncPt_struct junc : juncs) {
            if (junc == null) continue;
            List<Integer> compsInJunc = new ArrayList<>();
            for (int compId : junc.getCompIds()) {
                if (compId >= 1 && compId <= nComp) compsInJunc.add(compId);
            }
            for (int i = 0; i < compsInJunc.size(); i++) {
                for (int j = i + 1; j < compsInJunc.size(); j++) {
                    List<Integer> pair = new ArrayList<>();
                    pair.add(compsInJunc.get(i));
                    pair.add(compsInJunc.get(j));
                    Collections.sort(pair);
                    if (seen.add(pair)) pairs.add(pair);
                }
            }
        }
        return pairs;
    }

    /** A sibling variant of this variant's parent: the parent-numbered comp(s) it preserved + response. */
    private static class SiblingVariant {
        final List<Integer> preservedComps;
        final Double response;
        SiblingVariant(List<Integer> preservedComps, Double response) {
            this.preservedComps = preservedComps;
            this.response = response;
        }
    }

    /**
     * Every variant sibling of this variant's parent, with the comp(s) it preserved (in the parent's
     * numbering, from its HypothesizedComp.parent_hypothesized_comps) and its response (null = not yet
     * collected). This variant's own row, if already written, contributes nothing (null response).
     */
    private List<SiblingVariant> readSiblingVariants() {
        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        List idAndResponse = jt.query(
                "SELECT stim_id, response FROM StimGaInfo WHERE parent_id = ? AND stim_type = ?",
                new Object[]{parentId, StimType.REGIME_ESTIM_VARIANTS.getValue()},
                new RowMapper() {
                    public Object mapRow(ResultSet rs, int rowNum) throws SQLException {
                        long siblingId = rs.getLong("stim_id");
                        double resp = rs.getDouble("response");
                        Double response = rs.wasNull() ? null : resp;
                        return new Object[]{siblingId, response};
                    }
                });
        List<SiblingVariant> out = new ArrayList<>();
        for (Object o : idAndResponse) {
            Object[] row = (Object[]) o;
            Long siblingId = (Long) row[0];
            Double response = (Double) row[1];
            List<Integer> preserved = Collections.emptyList();
            if (hypothesizedCompManager.hasProperty(siblingId)) {
                List<Integer> c = hypothesizedCompManager.readProperty(siblingId).getParentHypothesizedComps();
                if (c != null) preserved = c;
            }
            out.add(new SiblingVariant(preserved, response));
        }
        return out;
    }

    /** Most-recent value of a GAVar, or {@code defaultValue} if absent/unreadable. */
    protected double readGaVarDouble(String name, double defaultValue) {
        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        try {
            String v = (String) jt.queryForObject(
                    "SELECT value FROM GAVar WHERE name = ? ORDER BY experiment_id DESC, gen_id DESC, arr_ind ASC LIMIT 1",
                    new Object[]{name}, String.class);
            if (v != null && !v.trim().isEmpty()) return Double.parseDouble(v.trim());
        } catch (Exception e) {
            // missing table/row or non-numeric -> default
        }
        return defaultValue;
    }

    /** A stim's GA response, or 0 if missing. */
    protected double readResponse(Long stimId) {
        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        try {
            Double r = (Double) jt.queryForObject(
                    "SELECT response FROM StimGaInfo WHERE stim_id = ?", new Object[]{stimId}, Double.class);
            return r != null ? r : 0.0;
        } catch (Exception e) {
            return 0.0;
        }
    }

    /** Component indices from {@code comps} that exist in a shape with {@code nComp} comps (1-based). */
    protected List<Integer> inRange(List<Integer> comps, int nComp) {
        List<Integer> valid = new ArrayList<>();
        if (comps != null) {
            for (Integer c : comps) {
                if (c != null && c >= 1 && c <= nComp) valid.add(c);
            }
        }
        return valid;
    }

    /** Leaf (terminal) component indices of the parent shape, 1-based. */
    protected List<Integer> leavesOf(GAMatchStick parentMStick) {
        parentMStick.decideLeafBranch();
        boolean[] leafBranch = parentMStick.getLeafBranch();
        List<Integer> leaves = new ArrayList<>();
        for (int i = 1; i <= parentMStick.getNComponent() && i < leafBranch.length; i++) {
            if (leafBranch[i]) leaves.add(i);
        }
        return leaves;
    }
}
