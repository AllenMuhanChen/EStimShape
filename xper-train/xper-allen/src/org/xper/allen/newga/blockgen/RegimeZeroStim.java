package org.xper.allen.newga.blockgen;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.ga3d.blockgen.GABlockGenerator;
import org.xper.allen.ga3d.blockgen.ThreeDGAStim;
import org.xper.allen.pga.StimType;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public class RegimeZeroStim extends ThreeDGAStim<MorphedMatchStick, AllenMStickData> {
    public RegimeZeroStim(GABlockGenerator generator, double size, Coordinates2D coords) {
        super(generator, size, coords);
        this.stimType = StimType.REGIME_ZERO.getValue();
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        MorphedMatchStick mStick = new MorphedMatchStick();
        mStick.setProperties(generator.getMaxImageDimensionDegrees(), "SHADE");
        mStick.genMatchStickRand();

        writeMStickData(mStick);
        String pngPath = drawPngs(mStick);

        writeSpecs(pngPath);
    }

    private void writeMStickData(MorphedMatchStick mStick) {
        //IMPORTANT that mStickSpec info is written before getMStickData()
        // because getMStickData() has side effects.
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick, true);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
        mStickData = mStick.getMStickData();
    }

    private String drawPngs(MorphedMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(generator.getGaBaseName());
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);
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