package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.ga.regimescore.MutationType;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;


public class RegimeOneStim extends MorphedStim<GrowingMatchStick, AllenMStickData> {


    public RegimeOneStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.stimType = NewGABlockGenerator.STIM_TYPE_FOR_REGIME.get(MutationType.ONE);
    }


    @Override
    protected GrowingMatchStick morphStim() {
        //Generate MStick
        GrowingMatchStick parentMStick = new GrowingMatchStick();
        parentMStick.setProperties(generator.getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        GrowingMatchStick childMStick = new GrowingMatchStick();
        childMStick.setProperties(generator.getMaxImageDimensionDegrees());
        childMStick.genGrowingMatchStick(parentMStick, 0.3);
        return childMStick;
    }

    @Override
    protected void writeMStickData(GrowingMatchStick mStick) {
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();
    }

}