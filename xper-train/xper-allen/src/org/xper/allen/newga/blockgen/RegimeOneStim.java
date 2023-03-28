package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;

public class RegimeOneStim extends MorphedStim {

    public RegimeOneStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
    }

    @Override
    public void preWrite() {

    }

    @Override
    protected MorphedMatchStick morphStim() {
        //Generate MStick
        GrowingMatchStick parentMStick = new GrowingMatchStick();
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick mStick = new GrowingMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees());
        mStick.genGrowingMatchStick(parentMStick, 0.2);
        return mStick;
    }

}