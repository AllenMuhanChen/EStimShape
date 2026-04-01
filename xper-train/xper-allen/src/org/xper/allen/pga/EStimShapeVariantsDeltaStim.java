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

    public EStimShapeVariantsDeltaStim(Long stimId, FromDbGABlockGenerator generator, Long parentId) {
        super(stimId, generator, parentId);
    }

    @Override
    protected void choosePosition() {
        MStickPosition parentLocation = positionManager.readProperty(parentId);
        // could be another variant or a growing stick or zooming or whatever...
        if (parentLocation.positioningStrategy == PositioningStrategy.PRESERVED_COMP_BASED){
//            position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
              position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
        } else{
            throw new IllegalArgumentException("Delta parent's positioning strategy should have to be preserved comp based");
        }
    }


    @Override
    protected PruningMatchStick createMStick() {
        MStickPosition parentPosition = positionManager.readProperty(parentId);
        PruningMatchStick parentMStick = new PruningMatchStick(parentPosition.getPosition(), generator.getNoiseMapper());
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");


        // Read or choose components to preserve from parent

        List<Integer> compsToMutateInParent = preservedComponentData.getCompsToPreserve();

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
        Random random = new Random();
        boolean r = random.nextBoolean();
        double magnitude = random.nextDouble() * 0.3 + 0.5;


        childMStick.genNewComponentsMatchStick(parentMStick, compsToMutateInParent, magnitude, 0.5,
                true, 15, compsToMutateInParent);

        // Save data for this stimulus
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
        position.setPosition(childMStick.getMassCenterForComponent(compsToPreserveInNextChild.get(0)));
        position.setTargetComp(compsToPreserveInNextChild.get(0));
        PreservedComponentData childData = new PreservedComponentData(
                compsToPreserveInNextChild,
                parentId,
                compsToMutateInParent
        );
//        compsToPreserveManager.writeProperty(stimId, childData);

        //TODO: perhaps add manager for writing relationship between this stim and parentId in here? i.e explicit table

        return childMStick;
    }
}
