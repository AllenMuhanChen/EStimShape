package org.xper.allen.pga;

import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Random;

public class EStimShapeVariantsDeltaStim extends EStimShapeVariantsGAStim{

    private final double magnitude;

    public EStimShapeVariantsDeltaStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double magnitude) {
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
     * Which component this delta should mutate, per the GA's instruction on this delta's own
     * HypothesizedComp row. Python writes the row to drive the predict -> explore -> exploit
     * progression; the Java side does no random exploration on its own.
     *
     *   - no row              -> PREDICT: mutate the parent's hypothesized (predicted) comp
     *   - row, comp empty      -> EXPLORE: mutate a random component different from the predicted one
     *   - row, comp present    -> EXPLOIT: mutate exactly that component
     *
     * hypothesizedCompData holds the PARENT's row here (set by chooseHypothesizedComp()), so its
     * hypothesized comp is the predicted comp this delta would otherwise mutate. A non-variant
     * parent may have no predicted comp (null), in which case there is nothing to predict and we
     * explore a random component.
     */
    private List<Integer> chooseCompsToMutate(PruningMatchStick parentMStick) {
        List<Integer> predictedComp = (hypothesizedCompData != null) ? hypothesizedCompData.getHypothesizedComp() : null;
        if (!hypothesizedCompManager.hasProperty(stimId)) {
            // PREDICT: mutate the parent's predicted comp; with none, explore instead.
            if (predictedComp != null && !predictedComp.isEmpty()) {
                return predictedComp;
            }
            return randomComp(parentMStick, predictedComp);
        }
        List<Integer> instructed = hypothesizedCompManager.readProperty(stimId).getParentHypothesizedComps();
        if (instructed != null && !instructed.isEmpty()) {
            return instructed; // EXPLOIT
        }
        return randomComp(parentMStick, predictedComp); // EXPLORE
    }

    /** A random, non-empty set of components to mutate, avoiding {@code avoid} (the predicted comp) when given. */
    private List<Integer> randomComp(PruningMatchStick parentMStick, List<Integer> avoid) {
        List<Integer> explored = Collections.emptyList();
        while (explored.isEmpty() || explored.equals(avoid)) {
            explored = PruningMatchStick.chooseRandomComponentsToPreserve(parentMStick);
        }
        return explored;
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

        // Save data for this stimulus
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
        position.setPosition(childMStick.getMassCenterForComponent(compsToPreserveInNextChild.get(0)));
        position.setTargetComp(compsToPreserveInNextChild.get(0));
        // Record what this delta actually mutated. parent_hypothesized_comps = compsToMutateInParent
        // (the tested comp, in the parent's numbering) is what Python's exploit step and the NAFC
        // generators read back. Assigning the field lets the inherited writeStimProperties persist
        // it; previously this row was left as a stale copy of the parent's, which was wrong whenever
        // a random/forced comp (not the parent's hypothesized comp) was mutated.
        hypothesizedCompData = new HypothesizedCompData(
                compsToPreserveInNextChild,
                parentId,
                compsToMutateInParent
        );

        return childMStick;
    }
}
