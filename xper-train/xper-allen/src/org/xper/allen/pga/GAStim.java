package org.xper.allen.pga;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public abstract class GAStim<T extends MorphedMatchStick, D extends AllenMStickData> implements Stim {
    protected final FromDbGABlockGenerator generator;
    protected final Long parentId;
    protected final double size;
    protected final Coordinates2D coords;
    protected Long stimId;

    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords) {
        this.stimId = stimId;
        this.generator = generator;
        this.parentId = parentId;
        this.size = size;
        this.coords = coords;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        T mStick = createMStick();
        saveMStickSpec(mStick);

        D mStickData = (D) mStick.getMStickData();
        String pngPath = drawPngs(mStick);

        writeStimSpec(pngPath, mStickData);
    }


    protected abstract T createMStick();

    @Override
    public Long getTaskId() {
        return stimId;
    }

    private String drawPngs(MorphedMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);
        return pngPath;
    }

    private void saveMStickSpec(T mStick) {
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
    }

    private void writeStimSpec(String pngPath, D mStickData) {
        PngSpec stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(size, size));
        stimSpec.setxCenter(coords.getX());
        stimSpec.setyCenter(coords.getY());

        generator.getDbUtil().writeStimSpec(stimId, stimSpec.toXml(), mStickData.toXml());
    }
}