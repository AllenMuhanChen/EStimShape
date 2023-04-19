package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.ga3d.blockgen.ThreeDGAStim;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public class RegimeZeroStim extends ThreeDGAStim<MorphedMatchStick, AllenMStickData> {
    public RegimeZeroStim(NewGABlockGenerator generator, double size, Coordinates2D coords) {
        super(generator, size, coords);
        this.stimType = NewGABlockGenerator.stimTypeForRegime.get(Regime.ZERO);
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        MorphedMatchStick mStick = new MorphedMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees());
        mStick.genMatchStickRand();

        writeMStickData(mStick);
        String pngPath = drawPngs(mStick);

        writeSpecs(pngPath);
    }

    private void writeMStickData(MorphedMatchStick mStick) {
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();
    }

    private String drawPngs(MorphedMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(generator.getGaBaseName());
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPathToExperiment(pngPath);
        return pngPath;
    }

    private void writeSpecs(String pngPath) {
        stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(size, size));
        stimSpec.setxCenter(coords.getX());
        stimSpec.setyCenter(coords.getY());

        writeStimSpec(stimId);
    }

    @Override
    public Long getStimId() {
        return stimId;
    }
}