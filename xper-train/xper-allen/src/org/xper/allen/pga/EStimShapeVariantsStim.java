package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.stimproperty.CompsToPreserveManager;
import org.xper.drawing.stick.stickMath_lib;

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
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        double sizeMagnitude = 0.25;

        double maxSizeDiameterDegrees = RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees());
        double minSizeDiameterDegrees = maxSizeDiameterDegrees / 2;
        double parentSizeDiameterDegrees = sizeManager.readProperty(parentId);
        double maxSizeMutation = (maxSizeDiameterDegrees - minSizeDiameterDegrees);
        double randomChange = (random.nextDouble() * sizeMagnitude * 2 - 1) * maxSizeMutation;
        sizeDiameterDegrees = Math.min(maxSizeDiameterDegrees, Math.max(minSizeDiameterDegrees, parentSizeDiameterDegrees + randomChange));
    }

    @Override
    protected PruningMatchStick createMStick() {
        GAMatchStick parentMStick = new GAMatchStick(generator.getReceptiveField(), null);
        parentMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        PruningMatchStick childMStick = new PruningMatchStick(generator.getNoiseMapper());
        childMStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        childMStick.setStimColor(color);

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
        if (random.nextBoolean()) {
            double magnitude = random.nextDouble() * 0.4 + 0.5;
            childMStick.genPruningMatchStick(parentMStick, magnitude, compsToPreserveInParent, null);
        } else {
            int nComp = 0;
            while (nComp < compsToPreserveInParent.size()) {
                nComp = stickMath_lib.pickFromProbDist(PruningMatchStick.PARAM_nCompDist);
            }
            childMStick.genMatchStickFromComponentsInNoise(parentMStick, compsToPreserveInParent, nComp,
                    true, 15);
        }

        // Save data for this stimulus
        List<Integer> compsToPreserveInNextChild = childMStick.getPreservedComps();
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
