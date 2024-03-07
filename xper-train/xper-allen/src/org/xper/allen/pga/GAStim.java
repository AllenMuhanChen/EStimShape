package org.xper.allen.pga;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.RFMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public abstract class GAStim<T extends RFMatchStick, D extends AllenMStickData> implements Stim {
    protected final FromDbGABlockGenerator generator;
    protected final Long parentId;
    protected final double size;
    protected final Coordinates2D coords;
    protected Long stimId;
    protected String textureType;

    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords) {
        this.stimId = stimId;
        this.generator = generator;
        this.parentId = parentId;
        this.size = size;
        this.coords = coords;
        this.textureType = "SHADE";
    }

    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double size, Coordinates2D coords, String textureType) {
        this.generator = generator;
        this.parentId = parentId;
        this.size = size;
        this.coords = coords;
        this.stimId = stimId;
        this.textureType = textureType;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        int nTries = 0;
        T mStick = null;
        while(nTries < 10) {
            try {
                nTries++;
                mStick = createMStick();
            } catch (MorphedMatchStick.MorphException me) {
                System.out.println("Morphing failed, trying again with new parameters");
            }
        }

        if (nTries == 10) {
            mStick = createRandMStick();
        }


        saveMStickSpec(mStick);

        D mStickData = (D) mStick.getMStickData();
        drawCompMaps(mStick);
        String pngPath = drawPngs(mStick);
        writeStimSpec(pngPath, mStickData);
    }

    private T createRandMStick() {
        RFMatchStick mStick = new RFMatchStick();
        mStick.setProperties(calculateSize(), textureType);
        mStick.setStimColor(getRFColor());
        mStick.genMatchStickRand();
        return (T) mStick;
    }

    protected void drawCompMaps(T mStick) {
        List<String> labels = new LinkedList<>();
        generator.getPngMaker().createAndSaveCompMap(mStick, stimId, labels, generator.getGeneratorPngPath());
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
        mStickSpec.setMStickInfo(mStick, true);
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

    protected double calculateSize() {
        Coordinates2D rfCenter = generator.rfSource.getRFCenter();
        double size = 1.5 * Math.sqrt(Math.pow(rfCenter.getY(), 2) + Math.pow(rfCenter.getX(), 2));
        System.out.println("Size: " + size);
        return size;
    }

    public org.xper.utils.RGBColor getRFColor(){
        org.xper.utils.RGBColor rfColor;
        try {
            rfColor = new org.xper.utils.RGBColor(generator.rfSource.getRFColor());

        } catch (Exception e) {
            System.out.println("Error getting RF color, using default color: white");
            rfColor = new org.xper.utils.RGBColor(1, 1, 1);
        }
        return rfColor;
    }
}