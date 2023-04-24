package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.PruningMatchStick;
import org.xper.allen.drawing.composition.morph.PruningMatchStick.PruningMStickData;
import org.xper.allen.ga.regimescore.Regime;

import java.util.LinkedList;
import java.util.List;

import static org.xper.allen.newga.blockgen.NewGABlockGenerator.stimTypeForRegime;

public class RegimeThreeStim extends MorphedStim<ExploreMatchStick, AllenMStickData> {

    private NewGABlockGenerator generator;
    public RegimeThreeStim(NewGABlockGenerator generator, Long parentId) {
        super(generator, parentId);
        this.generator = generator;
        this.stimType = stimTypeForRegime.get(Regime.THREE);
    }

    @Override
    protected ExploreMatchStick morphStim() {
        PruningMatchStick parentMStick = new PruningMatchStick();
        parentMStick.setProperties(getGenerator().getMaxImageDimensionDegrees());
        parentMStick.genMatchStickFromFile(getGenerator().getGeneratorSpecPath() + "/" + parentId + "_spec.xml");

        RegimeThreeComponentChooser chooser = new RegimeThreeComponentChooser(getGenerator().getDbUtil(), getGenerator().getSlotSelectionProcess().getSpikeRateSource());
        List<Integer> compsToMorph = chooser.choose(parentId, 1);

        ExploreMatchStick childMStick = new ExploreMatchStick(parentMStick, compsToMorph);
        childMStick.setProperties(getGenerator().getMaxImageDimensionDegrees());
        childMStick.genExploreMatchStick(rollMagnitude());
        return childMStick;
    }

    private double rollMagnitude() {
        return Math.random() * 0.3 + 0.2;
    }

    @Override
    protected void writeMStickData(ExploreMatchStick mStick){
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