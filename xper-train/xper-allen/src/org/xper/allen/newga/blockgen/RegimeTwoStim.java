package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick.PruningMStickData;
import org.xper.allen.ga.regimescore.MutationType;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;


public class RegimeTwoStim extends MorphedStim<PruningMatchStick, PruningMStickData> {

    public RegimeTwoStim(GABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.stimType = SlotGABlockGenerator.STIM_TYPE_FOR_REGIME.get(MutationType.TWO);
    }

    @Override
    protected PruningMatchStick morphStim(double magnitude) {
        PruningMatchStick parentMStick = new PruningMatchStick();
        parentMStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
        parentMStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        PruningMatchStick childMStick = new PruningMatchStick();
        childMStick.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
        childMStick.genPruningMatchStick(parentMStick, 0.75, 1);
        return childMStick;

    }

    @Override
    protected void writeMStickData(PruningMatchStick mStick){
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick, true);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();
    }

}