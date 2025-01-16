package org.xper.allen.twodvsthreed;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.MStickData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.stimproperty.ColorPropertyManager;
import org.xper.allen.stimproperty.RFStrategyPropertyManager;
import org.xper.allen.stimproperty.SizePropertyManager;
import org.xper.allen.stimproperty.TexturePropertyManager;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import java.util.LinkedList;
import java.util.List;

public class TwoDVsThreeDStim implements Stim {
    private final RFStrategyPropertyManager rfStrategyManager;
    private final SizePropertyManager sizeManager;
    private final RFStrategy rfStrategy;
    private final double sizeDiameterDegrees;
    private final ColorPropertyManager colorManager;
    private final TexturePropertyManager textureManager;
    TwoDVsThreeDTrialGenerator generator;
    long targetStimId;
    String textureType;
    RGBColor color;
    private String targetSpecPath;
    private ReceptiveField receptiveField;
    private Long stimId;
    private Coordinates2D imageCenterCoords = new Coordinates2D(0, 0);;

    public TwoDVsThreeDStim(TwoDVsThreeDTrialGenerator generator, long targetStimId, String textureType, RGBColor color) {
        this.generator = generator;
        this.targetStimId = targetStimId;
        this.textureType = textureType;
        this.color = color;


        rfStrategyManager = new RFStrategyPropertyManager(new JdbcTemplate(generator.gaDataSource));
        sizeManager = new SizePropertyManager(new JdbcTemplate(generator.gaDataSource));
        colorManager = new ColorPropertyManager(new JdbcTemplate(generator.gaDataSource));
        textureManager = new TexturePropertyManager(new JdbcTemplate(generator.gaDataSource));


        rfStrategy = rfStrategyManager.readProperty(targetStimId);
        sizeDiameterDegrees = sizeManager.readProperty(targetStimId);


        targetSpecPath = generator.gaSpecPath + "/" + targetStimId + "_spec.xml";
        receptiveField = generator.rfSource.getReceptiveField();
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();

        GAMatchStick mStick = new GAMatchStick(receptiveField, rfStrategy);
        mStick.setProperties(sizeDiameterDegrees, textureType);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(targetSpecPath, new double[]{0,0,0});
//
        saveMStickSpec(mStick);
        String pngPath = drawPng(mStick);
        AllenMStickData mStickData = (AllenMStickData) mStick.getMStickData();
        writeStimSpec(pngPath, mStickData);

        writeStimProperties();
    }

    private void writeStimProperties() {
        colorManager.writeProperty(stimId, color);
        textureManager.writeProperty(stimId, textureType);
        sizeManager.writeProperty(stimId, (float) sizeDiameterDegrees);
        rfStrategyManager.writeProperty(stimId, rfStrategy);
    }

    protected String drawPng(AllenMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);
        return pngPath;
    }


    protected void writeStimSpec(String pngPath, AllenMStickData mStickData) {
        double imageSizeDeg = generator.getImageDimensionsDegrees();

        PngSpec stimSpec = new PngSpec();
        stimSpec.setPath(pngPath);
        stimSpec.setDimensions(new ImageDimensions(imageSizeDeg, imageSizeDeg));
        stimSpec.setxCenter(imageCenterCoords.getX());
        stimSpec.setyCenter(imageCenterCoords.getY());

        ((AllenDbUtil) generator.getDbUtil()).writeStimSpec(stimId, stimSpec.toXml(), mStickData.toXml());
    }

    private void saveMStickSpec(GAMatchStick mStick) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick, true);
        spec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
    }

    @Override
    public Long getStimId() {
        return stimId;
    }
}