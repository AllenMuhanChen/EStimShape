package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.ga.regimescore.MutationType;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;

import static org.xper.allen.newga.blockgen.SlotGABlockGenerator.STIM_TYPE_FOR_REGIME;

public class OldRegimeThreeStim extends MorphedStim<GrowingMatchStick, AllenMStickData> {

    public OldRegimeThreeStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.stimType = STIM_TYPE_FOR_REGIME.get(MutationType.THREE);
    }

    @Override
    protected GrowingMatchStick morphStim(double magnitude) {
        GrowingMatchStick parentMStick = new GrowingMatchStick(1.0);
        parentMStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick();
        childMStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
        childMStick.genGrowingMatchStick(parentMStick, rollMagnitude());
        return childMStick;
    }

    private double rollMagnitude() {
        return Math.random() * 0.2 + 0.1;
    }
}