package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;


public class RegimeOneStim extends MorphedStim {


    public RegimeOneStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.stimType = NewGABlockGenerator.stimTypeForRegime.get(Regime.ONE);
    }


    @Override
    protected MorphedMatchStick morphStim() {
        //Generate MStick
        GrowingMatchStick parentMStick = new GrowingMatchStick();
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genGrowingMatchStick(parentMStick, 0.3);
        return childMStick;
    }

}