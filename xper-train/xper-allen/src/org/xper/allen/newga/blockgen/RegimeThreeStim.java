package org.xper.allen.newga.blockgen;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;

public class RegimeThreeStim extends MorphedStim {

    public RegimeThreeStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.stimType = NewGABlockGenerator.stimTypeForRegime.get(NewGABlockGenerator.Regime.THREE);
    }

    @Override
    protected MorphedMatchStick morphStim() {
        //Generate MStick
        GrowingMatchStick parentMStick = new GrowingMatchStick();
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genGrowingMatchStick(parentMStick, getMagnitude());
        return childMStick;
    }

    //TODO: have magnitude determined by current balance of magnitudes
    private double getMagnitude(){
        return Math.random();
    }
}