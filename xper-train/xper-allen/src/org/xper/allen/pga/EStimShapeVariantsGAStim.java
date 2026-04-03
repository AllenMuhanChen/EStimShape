package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import java.util.List;
import java.util.Random;

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

//        List<Integer> compsToPreserveInParent = preservedComponentData.getCompsToPreserve();
        List<Integer> compsToPreserveInParent;
        if (shouldPreserveRandomComps()) {
            compsToPreserveInParent = PruningMatchStick.chooseRandomComponentsToPreserve(parentMStick);
        } else {
            PreservedComponentData parentData = compsToPreserveManager.readProperty(parentId);
            compsToPreserveInParent = parentData.getCompsToPreserve();
        }

        // Generate child
        Random random = new Random();
        boolean r = random.nextBoolean();

        if (r) {
            double magnitude = random.nextDouble() * 0.4 + 0.5;
            childMStick.genPruningMatchStick(parentMStick, magnitude, compsToPreserveInParent, null);
        }
        else {
            int nComp = 0;
            while (nComp <= compsToPreserveInParent.size()) {
                nComp = stickMath_lib.pickFromProbDist(PruningMatchStick.PARAM_nCompDist);
            }
            childMStick.genMatchStickFromComponentsInNoise(parentMStick, compsToPreserveInParent, nComp,
                    true, 15);
        }

        // Save data for this stimulus
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
        position.setPosition(childMStick.getMassCenterForComponent(compsToPreserveInNextChild.get(0)));
        position.setTargetComp(compsToPreserveInNextChild.get(0));
        preservedComponentData = new PreservedComponentData(
                compsToPreserveInNextChild,
                parentId,
                compsToPreserveInParent
        );
//        compsToPreserveManager.writeProperty(stimId, childData); //shouldn't have to do this now, we put this in GAStim

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
    protected boolean shouldPreserveRandomComps() {
        // We want to assign new comps to preserve if it has preservation history AND is delta or growing
        if (parentHasCompsToPreserve()){ //has preservation history
            if (stimTypeManager.readProperty(parentId) == StimType.REGIME_ONE){
                return true; // if it's regime one, we probably have changed the preserved comp and other comps, so we don't know what's driving response, need to re-test.
            }
            Random r = new Random();
            return r.nextDouble() < magnitude;
        }
        else{
            return true;
        }

    }

    protected boolean parentHasCompsToPreserve() {
        return compsToPreserveManager.hasProperty(parentId);
    }
}
