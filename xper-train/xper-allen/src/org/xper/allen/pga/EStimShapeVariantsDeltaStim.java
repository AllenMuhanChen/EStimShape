package org.xper.allen.pga;

import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.stick.stickMath_lib;

import java.util.List;
import java.util.Random;

public class EStimShapeVariantsDeltaStim extends EStimShapeVariantsGAStim{

    public EStimShapeVariantsDeltaStim(Long stimId, FromDbGABlockGenerator generator, Long parentId) {
        super(stimId, generator, parentId);
    }

    @Override
    protected PruningMatchStick createMStick() {
        PruningMatchStick parentMStick = new PruningMatchStick(generator.getReceptiveField(), null, null);
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

        // Read or choose components to preserve from parent
        List<Integer> compsToMutateInParent;
        if (!parentHasCompsToPreserve()){
            throw new IllegalArgumentException("This stim should have comps to preserve when making a delta shape version");
        } else {
            PreservedComponentData parentData = compsToPreserveManager.readProperty(parentId);
            compsToMutateInParent = parentData.getCompsToPreserve();
        }

        // Generate child
        Random random = new Random();
        boolean r = random.nextBoolean();


        double magnitude = random.nextDouble() * 0.3 + 0.5;
        childMStick.setPreservedComps(compsToMutateInParent);
        childMStick.genNewComponentsMatchStick(parentMStick, compsToMutateInParent, magnitude, 0.5,true, 15, compsToMutateInParent);

        // Save data for this stimulus
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
        position.setPosition(childMStick.getMassCenterForComponent(compsToPreserveInNextChild.get(0)));
        position.setTargetComp(compsToPreserveInNextChild.get(0));
        PreservedComponentData childData = new PreservedComponentData(
                compsToPreserveInNextChild,
                parentId,
                compsToMutateInParent
        );
        compsToPreserveManager.writeProperty(stimId, childData);

        //TODO: perhaps add manager for writing relationship between this stim and parentId in here? i.e explicit table

        return childMStick;
    }
}
