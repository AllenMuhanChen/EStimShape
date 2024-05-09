package org.xper.allen.pga;

import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
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
    protected final Coordinates2D imageCenterCoords;
    protected Long stimId;
    protected String textureType;
    protected RGBColor color;
    private double marginMultiplier = 0.5;

    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Coordinates2D coords, String textureType, RGBColor color, RFStrategy rfStrategy) {
        this.generator = generator;
        this.parentId = parentId;
        this.imageCenterCoords = coords;
        this.stimId = stimId;
        this.textureType = textureType;
        this.color = color;
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        int nTries = 0;
        T mStick = null;
        while(nTries < 100) {
            nTries++;
            try {
                mStick = createMStick();
                System.out.println("SUCCESSFUL CREATION OF MORPHED MATCHSTICK OF TYPE: " + this.getClass().getSimpleName());
                break;
            } catch (MorphedMatchStick.MorphException me) {
                mStick = null;
                System.out.println("Morphing failed, trying again with new parameters");
            }
        }

        if (nTries == 10 && mStick == null) {
            System.err.println("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName()+"AFTER 10 TRIES. GENERATING RAND...");
            mStick = createRandMStick();
        }


        saveMStickSpec(mStick);

        D mStickData = (D) mStick.getMStickData();
        drawCompMaps(mStick);
        String pngPath = drawPngs(mStick);
        writeStimSpec(pngPath, mStickData);
    }

    private T createRandMStick() {
        RFMatchStick mStick = new RFMatchStick(generator.getReceptiveField(), 0.2);
        mStick.setProperties(calculateImageSize(), textureType);
        mStick.setStimColor(color);
        mStick.genMatchStickRand();
        return (T) mStick;
    }

    protected void drawCompMaps(T mStick) {
        List<String> labels = new LinkedList<>();
        generator.getPngMaker().createAndSaveCompMap(mStick, stimId, labels, generator.getGeneratorPngPath());
    }

    protected abstract T createMStick();

    @Override
    public Long getStimId() {
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
        double imageSizeDeg = generator.getImageDimensionsDegrees();

        PngSpec stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(imageSizeDeg, imageSizeDeg));
        stimSpec.setxCenter(imageCenterCoords.getX());
        stimSpec.setyCenter(imageCenterCoords.getY());

        generator.getDbUtil().writeStimSpec(stimId, stimSpec.toXml(), mStickData.toXml());
    }

    /**
     * Idea is to have image centered at fixation and large enough so that part of the shape
     * can extend into and then out the other side of the RF.
     * @return
     */
    protected double calculateImageSize() {
        Coordinates2D rfCenter = generator.rfSource.getRFCenter();
        double eccentricity = Math.sqrt(Math.pow(rfCenter.getX() - imageCenterCoords.getX(), 2) + Math.pow(rfCenter.getY() - imageCenterCoords.getY(), 2));
        double distanceFromImageCenterToEdgeOfRf = eccentricity + generator.rfSource.getRFRadius();
        double margin = marginMultiplier * distanceFromImageCenterToEdgeOfRf;
        double imageSizeInDegrees = distanceFromImageCenterToEdgeOfRf + margin;
        System.out.println("Image size in degrees: " + imageSizeInDegrees);
        return imageSizeInDegrees;
    }

//    public RGBColor getRFColor(){
//        RGBColor rfColor;
//        try {
//            rfColor = new RGBColor(generator.rfSource.getRFColor());
//
//        } catch (Exception e) {
//            System.out.println("Error getting RF color, using default color: white");
//            rfColor = new RGBColor(1, 1, 1);
//        }
//        return rfColor;
//    }
}