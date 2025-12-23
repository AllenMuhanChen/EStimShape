package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.experiment.PositioningStrategy;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.stimproperty.CompsToPreserveManager;
import org.xper.drawing.stick.stickMath_lib;

import javax.vecmath.Point3d;
import java.util.List;
import java.util.Random;

public class EStimShapeVariantsStim extends GAStim<PruningMatchStick, AllenMStickData>{
    private static final Random random = new Random();

    protected final CompsToPreserveManager compsToPreserveManager;
    public EStimShapeVariantsStim(Long stimId, FromDbGABlockGenerator generator, Long parentId) {
        super(stimId, generator, parentId);
        this.textureType = "PARENT";

        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.getDbUtil().getDataSource());
        compsToPreserveManager = new CompsToPreserveManager(jdbcTemplate);
    }

    @Override
    protected void choosePosition() {
        MStickPosition parentLocation = positionManager.readProperty(parentId);
        // could be another variant or a growing stick or zooming or whatever...
        if (parentLocation.positioningStrategy != PositioningStrategy.PRESERVED_COMP_BASED){
            position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, null);
        } else{
            Point3d oldPosition = parentLocation.getPosition();
            position = new MStickPosition(PositioningStrategy.PRESERVED_COMP_BASED, oldPosition);
        }
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

        // Read or choose components to preserve from parent
        List<Integer> compsToPreserveInParent;
        if (!parentHasCompsToPreserve()){
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
        PreservedComponentData childData = new PreservedComponentData(
                compsToPreserveInNextChild,
                parentId,
                compsToPreserveInParent
        );
        compsToPreserveManager.writeProperty(stimId, childData);

        return childMStick;
    }

    private boolean parentHasCompsToPreserve() {
        return compsToPreserveManager.hasProperty(parentId);
    }
}
