package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;


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

        PruningMatchStick childMStick = new PruningMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genPruningMatchStick(parentMStick, 0.6, 1);
        return childMStick;

    }

}