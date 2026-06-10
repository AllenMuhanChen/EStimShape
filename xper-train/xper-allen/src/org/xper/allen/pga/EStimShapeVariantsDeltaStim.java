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
     * Which of the parent's components this delta mutates.
     *
     * The parent's hypothesized comp(s) are the candidate drivers: for a variant that is its single
     * hypothesized driver; for a delta parent it is the comps that delta preserved (its mutation
     * didn't kill the response, so the driver is among what it kept) - pick one of those at random.
     * A parent with no hypothesis at all (e.g. regime_one) gets a fully random component.
     *
     * There is no explicit explore/exploit scheduling: high-response deltas become delta parents
     * themselves, so chaining deltas onto deltas naturally walks through the remaining candidate
     * components until one drops the response.
     */
    private List<Integer> chooseCompsToMutate(PruningMatchStick parentMStick) {
        List<Integer> candidates = (hypothesizedCompData != null) ? hypothesizedCompData.getHypothesizedComp() : null;
        if (candidates == null || candidates.isEmpty()) {
            List<Integer> random = Collections.emptyList();
            while (random.isEmpty()) {
                random = PruningMatchStick.chooseRandomComponentsToPreserve(parentMStick);
            }
            return random;
        }
        if (candidates.size() == 1) {
            return candidates;
        }
        Random r = new Random();
        return Collections.singletonList(candidates.get(r.nextInt(candidates.size())));
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
        // (the tested comp, in the parent's numbering) is what the NAFC generators read back, and
        // hypothesized_comp = the preserved comps becomes the candidate-driver set for any deltas
        // chained onto this one. Assigning the field lets the inherited writeStimProperties persist it.
        hypothesizedCompData = new HypothesizedCompData(
                compsToPreserveInNextChild,
                parentId,
                compsToMutateInParent
        );

        return childMStick;
    }
}
