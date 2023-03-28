package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.newga.blockgen.NewGABlockGenerator.Regime;

public class RegimeTwoStim extends MorphedStim {

    public RegimeTwoStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.stimType = NewGABlockGenerator.stimTypeForRegime.get(Regime.TWO);
    }

    @Override
    protected MorphedMatchStick morphStim() {
        PruningMatchStick parentMStick = new PruningMatchStick();
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genGrowingMatchStick(parentMStick, 0.6);
        return childMStick;

    }

}