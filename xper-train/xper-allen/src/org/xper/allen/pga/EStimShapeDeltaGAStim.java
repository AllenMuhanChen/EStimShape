package org.xper.allen.pga;

import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

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
     * Which of the parent's components this delta mutates.
     *
     * The hypothesized comp is THE FRAGMENT BEING TESTED, for every stim type: a variant tests it
     * by preserving it (response should stay high); a delta tests it by changing it (response
     * should drop). So the parent's hypothesized comp means opposite things for comp selection:
     *
     *  - Variant (or other) parent: its hypothesized comp is the predicted driver - change it.
     *  - Delta parent: it already CHANGED its hypothesized comp and (being a high-response parent)
     *    the response didn't drop, so that comp is refuted - change any comp EXCEPT it.
     *  - No hypothesis at all (e.g. regime_one): change a fully random component.
     *
     * There is no explicit explore/exploit scheduling: each high-response delta refutes one comp,
     * and chaining deltas onto deltas walks through the remaining candidates until one drops the
     * response.
     */
    private List<Integer> chooseCompsToMutate(PruningMatchStick parentMStick) {
        List<Integer> hypothesized = (hypothesizedCompData != null) ? hypothesizedCompData.getHypothesizedComp() : null;
        // Drop comp indices that don't exist in the parent shape. A growing/sidetest stim's row is
        // an inherited COPY of its own parent's row, in that grandparent's numbering; growing
        // mutation can renumber or add comps, so an inherited index may not map onto this parent.
        if (hypothesized != null) {
            List<Integer> valid = new ArrayList<>();
            for (Integer comp : hypothesized) {
                if (comp != null && comp >= 1 && comp <= parentMStick.getNComponent()) {
                    valid.add(comp);
                }
            }
            if (valid.size() < hypothesized.size()) {
                System.err.println("WARNING: parent " + parentId + " HypothesizedComp " + hypothesized +
                        " contains comp indices outside the parent shape (nComp=" +
                        parentMStick.getNComponent() + "); ignoring the out-of-range ones.");
            }
            hypothesized = valid;
        }

        List<Integer> candidates;
        if (hypothesized == null || hypothesized.isEmpty()) {
            candidates = Collections.emptyList();
        } else if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ESTIM_DELTA) {
            // Parent delta changed its hypothesized comp and the response stayed high: refuted.
            // Candidates are every other component.
            candidates = new ArrayList<>();
            for (int i = 1; i <= parentMStick.getNComponent(); i++) {
                if (!hypothesized.contains(i)) {
                    candidates.add(i);
                }
            }
        } else {
            // Variant parent: test its predicted driver by changing it.
            candidates = hypothesized;
        }

        // If there are no hypothesized comps, we're going to choose a new one right now.
        if (candidates.isEmpty()) {
            List<Integer> random = Collections.emptyList();
            while (random.isEmpty()) {
                random = PruningMatchStick.chooseRandomComponentsToPreserve(parentMStick);
            }
            return Collections.singletonList(random.get(0));
        }

        return Collections.singletonList(candidates.get(0));
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
