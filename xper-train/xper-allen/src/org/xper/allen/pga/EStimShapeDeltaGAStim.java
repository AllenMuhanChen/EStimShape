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
     *  1) Variant parent -> change its hypothesized (predicted-driver) comp(s).
     *  2) Non-variant parent (delta, growing, regime_one, ...) -> systematically search the parent's
     *     components, using the parent's existing delta-children as the record of what's been tried:
     *       a) some leaf hasn't been tested as a single-comp delta yet -> test an untested leaf;
     *       b) all leaves tested but NONE dropped the response past the GAVar threshold
     *          (delta_resp_ratio_threshold) -> explore two comps that share a junction;
     *       c) all leaves tested and SOME passed -> exploit them: pick a passing leaf with
     *          probability proportional to its response reduction. Recomputed every call from the
     *          current sibling responses, so the probabilities update as more deltas come back.
     */
    private List<Integer> chooseCompsToMutate(PruningMatchStick parentMStick) {
        int nComp = parentMStick.getNComponent();

        // 1) Variant parent: change its predicted driver.
        if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ESTIM_VARIANTS) {
            List<Integer> hypothesized = inRange(
                    hypothesizedCompData != null ? hypothesizedCompData.getHypothesizedComp() : null, nComp);
            return hypothesized.isEmpty()
                    ? Collections.singletonList(parentMStick.chooseRandLeaf())
                    : hypothesized;
        }

        // 2) Non-variant parent: tiered search over the parent's leaves.
        List<Integer> leaves = leavesOf(parentMStick);
        if (leaves.isEmpty()) {
            for (int i = 1; i <= nComp; i++) leaves.add(i);
        }

        List<SiblingDelta> siblings = readSiblingDeltas();

        // (a) Test a leaf that hasn't been tried as a single-comp delta yet.
        Set<Integer> testedLeaves = new HashSet<>();
        for (SiblingDelta s : siblings) {
            if (s.changedComps.size() == 1) testedLeaves.add(s.changedComps.get(0));
        }
        List<Integer> untested = new ArrayList<>();
        for (Integer leaf : leaves) {
            if (!testedLeaves.contains(leaf)) untested.add(leaf);
        }
        if (!untested.isEmpty()) {
            return Collections.singletonList(untested.get(new Random().nextInt(untested.size())));
        }

        // All leaves tested: best response-reduction ratio per leaf, from RESPONDED siblings.
        double parentResponse = readResponse(parentId);
        double threshold = readGaVarDouble("delta_resp_ratio_threshold", 0.5);
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
        List<Integer> passing = new ArrayList<>();
        for (Map.Entry<Integer, Double> e : bestRatio.entrySet()) {
            if (e.getValue() < threshold) passing.add(e.getKey());
        }

        // (b) Nothing single-comp dropped the response enough: explore two comps sharing a junction.
        if (passing.isEmpty()) {
            if (nComp >= 3) {
                List<Integer> pair = inRange(
                        PruningMatchStick.chooseRandomComponentsToPreserve(2, parentMStick), nComp);
                if (pair.size() == 2) return pair;
            }
            return Collections.singletonList(parentMStick.chooseRandLeaf());
        }

        // (c) Exploit: pick a passing leaf weighted by its response reduction (1 - ratio).
        return Collections.singletonList(weightedPickByReduction(passing, bestRatio));
    }

    /** Component indices from {@code comps} that exist in a shape with {@code nComp} comps (1-based). */
    private List<Integer> inRange(List<Integer> comps, int nComp) {
        List<Integer> valid = new ArrayList<>();
        if (comps != null) {
            for (Integer c : comps) {
                if (c != null && c >= 1 && c <= nComp) valid.add(c);
            }
        }
        return valid;
    }

    /** Leaf (terminal) component indices of the parent shape, 1-based. */
    private List<Integer> leavesOf(PruningMatchStick parentMStick) {
        parentMStick.decideLeafBranch();
        boolean[] leafBranch = parentMStick.getLeafBranch();
        List<Integer> leaves = new ArrayList<>();
        for (int i = 1; i <= parentMStick.getNComponent() && i < leafBranch.length; i++) {
            if (leafBranch[i]) leaves.add(i);
        }
        return leaves;
    }

    /** Pick a passing leaf with probability proportional to its response reduction (1 - ratio). */
    private Integer weightedPickByReduction(List<Integer> passing, Map<Integer, Double> bestRatio) {
        double total = 0;
        for (Integer leaf : passing) total += Math.max(1e-6, 1.0 - bestRatio.get(leaf));
        double r = new Random().nextDouble() * total;
        double cum = 0;
        for (Integer leaf : passing) {
            cum += Math.max(1e-6, 1.0 - bestRatio.get(leaf));
            if (r <= cum) return leaf;
        }
        return passing.get(passing.size() - 1);
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

    /** A stim's GA response, or 0 if missing. */
    private double readResponse(Long stimId) {
        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        try {
            Double r = (Double) jt.queryForObject(
                    "SELECT response FROM StimGaInfo WHERE stim_id = ?", new Object[]{stimId}, Double.class);
            return r != null ? r : 0.0;
        } catch (Exception e) {
            return 0.0;
        }
    }

    /** Most-recent value of a GAVar, or {@code defaultValue} if absent/unreadable. */
    private double readGaVarDouble(String name, double defaultValue) {
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

        return childMStick;
    }
}
