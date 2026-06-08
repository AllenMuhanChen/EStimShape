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
        MStickPosition parentLocation = positionManager.readProperty(parentId);
        // could be another variant or a growing stick or zooming or whatever...
        if (parentLocation.positioningStrategy == PositioningStrategy.PRESERVED_COMP_BASED){
//            position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
              position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
        } else{
            System.out.println("Parent positioning strategy: " + parentLocation.positioningStrategy);
            System.out.println("Parent Id: " + parentId);
            if (!hypothesizedCompManager.hasProperty(parentId)){
                throw new IllegalArgumentException("Delta parent's positioning strategy should have to be preserved comp based OR have stim comps to preserve");
            }
            position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);

        }
    }

    /**
     * Fallback policy for whether to mutate a randomly chosen component instead of the parent's
     * hypothesized comp. This only applies when Python has NOT pre-assigned a component for this
     * delta (see {@link #readForcedCompToMutate()}). Random exploration here is what generates the
     * alternative-component data that Python's exploit step later uses to pick the best comp.
     */
    @Override
    protected boolean shouldPreserveRandomComps() {
        Random r = new Random();
        return r.nextDouble() < magnitude;
    }

    /**
     * The component Python has decided this delta should mutate, or null if Python left the choice
     * to the Java side. Python pre-populates this delta's own HypothesizedComp row (with the
     * chosen comp in parent_hypothesized_comps) once a variant has accumulated enough failed delta
     * attempts that the GA wants to exploit the empirically best-dropping component. The chosen
     * comp is expressed in the parent's numbering, which is what we mutate against the parent here.
     */
    private List<Integer> readForcedCompToMutate() {
        if (hypothesizedCompManager.hasProperty(stimId)) {
            List<Integer> forced = hypothesizedCompManager.readProperty(stimId).getParentHypothesizedComps();
            if (forced != null && !forced.isEmpty()) {
                return forced;
            }
        }
        return null;
    }

    @Override
    protected PruningMatchStick createMStick() {
        MStickPosition parentPosition = positionManager.readProperty(parentId);
        PruningMatchStick parentMStick = new PruningMatchStick(parentPosition.getPosition(), generator.getNoiseMapper());
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        // Decide which parent component this delta mutates. Priority:
        //  1) a comp Python pre-assigned on THIS delta's own row (the GA's exploit choice);
        //  2) otherwise the legacy behavior: with probability `magnitude` explore a random comp,
        //     else mutate the parent's hypothesized comp.
        // hypothesizedCompData holds the PARENT's row here (set by chooseHypothesizedComp()).
        List<Integer> compsToMutateInParent = readForcedCompToMutate();
        if (compsToMutateInParent == null) {
            if (shouldPreserveRandomComps()){
                // redraw until we pick a comp different from the parent's hypothesized comp
                compsToMutateInParent = Collections.emptyList();
                while(compsToMutateInParent.isEmpty()
                        || compsToMutateInParent.equals(hypothesizedCompData.getHypothesizedComp()))
                    compsToMutateInParent = PruningMatchStick.chooseRandomComponentsToPreserve(parentMStick);
            }
            else {
                compsToMutateInParent = hypothesizedCompData.getHypothesizedComp();
            }
        }



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
