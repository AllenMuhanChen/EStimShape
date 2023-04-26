package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.GrowingMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.ga.regimescore.Regime;

import java.util.List;

import static org.xper.allen.newga.blockgen.NewGABlockGenerator.STIM_TYPE_FOR_REGIME;

public class RegimeThreeStim extends MorphedStim<MorphedMatchStick, AllenMStickData> {

    private NewGABlockGenerator generator;
    public RegimeThreeStim(NewGABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.generator = generator;
        this.stimType = STIM_TYPE_FOR_REGIME.get(Regime.THREE);
    }

    @Override
    protected MorphedMatchStick morphStim() {
        RegimeThreeComponentChooser chooser = new RegimeThreeComponentChooser(getGenerator().getDbUtil(), getGenerator().getSlotSelectionProcess().getSpikeRateSource());
        List<Integer> compsToMorph = chooser.choose(parentId, 1);

        PruningMatchStick parentMStick = new PruningMatchStick();
        parentMStick.setProperties(getGenerator().getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(getGenerator().getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        if ( chooser.getConfidence() > 0.75) {
            ExploreMatchStick childMStick = new ExploreMatchStick(parentMStick, compsToMorph);
            childMStick.setProperties(getGenerator().getMaxImageDimensionDegrees());
            childMStick.genExploreMatchStick(Math.random() * 0.3 + 0.2);
            return childMStick;
        }
        else{
            GrowingMatchStick childMStick = new GrowingMatchStick();
            childMStick.setProperties(generator.getMaxImageDimensionDegrees());
            childMStick.genGrowingMatchStick(parentMStick, Math.random() * 0.2 + 0.1);
            return childMStick;
        }
    }

    @Override
    protected void writeMStickData(MorphedMatchStick mStick){
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        mStickSpec.writeInfo2File(getGenerator().getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();
    }

    public NewGABlockGenerator getGenerator() {
        return generator;
    }

    public void setGenerator(NewGABlockGenerator generator) {
        this.generator = generator;
    }
}