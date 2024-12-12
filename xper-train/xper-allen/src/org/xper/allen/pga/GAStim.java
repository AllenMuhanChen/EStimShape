package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.stimproperty.ColorPropertyManager;
import org.xper.allen.stimproperty.SizePropertyManager;
import org.xper.allen.stimproperty.TexturePropertyManager;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public abstract class GAStim<T extends GAMatchStick, D extends AllenMStickData> implements Stim {
    protected final FromDbGABlockGenerator generator;
    protected final Long parentId;
    protected final Coordinates2D imageCenterCoords;
    protected final RFStrategy rfStrategy;
    protected final ColorPropertyManager colorManager;
    protected final TexturePropertyManager textureManager;
    protected final SizePropertyManager sizeManager;
    protected Long stimId;
    protected String textureType;
    protected RGBColor color;
    protected double sizeDiameterDegrees;

    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Coordinates2D coords, String textureType, RGBColor color, RFStrategy rfStrategy) {
        this.generator = generator;
        this.parentId = parentId;
        this.imageCenterCoords = coords;
        this.stimId = stimId;
        this.textureType = textureType;
        this.color = color;
        this.rfStrategy = rfStrategy;

        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.getDbUtil().getDataSource());
        colorManager = new ColorPropertyManager(jdbcTemplate);
        textureManager = new TexturePropertyManager(jdbcTemplate);
        sizeManager = new SizePropertyManager(jdbcTemplate);
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        int nTries = 0;
        T mStick = null;
        int maxTries = 100;
        while(nTries < maxTries) {
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

        if (nTries == maxTries && mStick == null) {
            System.err.println("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName()+"AFTER 10 TRIES. GENERATING RAND...");
            throw new RuntimeException("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName());
        }


        saveMStickSpec(mStick);

        D mStickData = (D) mStick.getMStickData();
        drawCompMaps(mStick);
        String pngPath = drawPngs(mStick);
        writeStimSpec(pngPath, mStickData);

        //write additional data here?
        writeStimData();
    }

    protected void writeStimData() {
        colorManager.writeProperty(stimId, color);
        textureManager.writeProperty(stimId, textureType);
        sizeManager.writeProperty(stimId, (float) sizeDiameterDegrees);
    }

    protected T createRandMStick() {
        GAMatchStick mStick = new GAMatchStick(generator.getReceptiveField(), rfStrategy);
        mStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees()), textureType);
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

    protected String drawPngs(MorphedMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        labels.add(Long.toString(parentId));
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);
        return pngPath;
    }

    protected void saveMStickSpec(T mStick) {
        AllenMStickSpec mStickSpec = new AllenMStickSpec();
        mStickSpec.setMStickInfo(mStick, true);
        mStickSpec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
    }

    protected void writeStimSpec(String pngPath, D mStickData) {
        double imageSizeDeg = generator.getImageDimensionsDegrees();

        PngSpec stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(imageSizeDeg, imageSizeDeg));
        stimSpec.setxCenter(imageCenterCoords.getX());
        stimSpec.setyCenter(imageCenterCoords.getY());

        generator.getDbUtil().writeStimSpec(stimId, stimSpec.toXml(), mStickData.toXml());
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