package org.xper.allen.twodvsthreed;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.ReceptiveField;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.stimproperty.*;
import org.xper.allen.util.AllenDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.png.ImageDimensions;
import org.xper.rfplot.drawing.png.PngSpec;

import javax.vecmath.Point3d;
import java.util.LinkedList;
import java.util.List;

public class TwoDVsThreeDStim implements Stim {
    protected final RFStrategyPropertyManager rfStrategyManager_ga;
    protected final SizePropertyManager sizeManager_ga;
    protected final RFStrategy rfStrategy;
    protected final double sizeDiameterDegrees;
    protected final ColorPropertyManager colorManager_ga;
    protected final TexturePropertyManager textureManager_ga;
    protected final ContrastPropertyManager contrastManager_ga;
    protected final RFStrategyPropertyManager rfStrategyManager_2dvs3d;
    protected final SizePropertyManager sizeManager_2dvs3d;
    protected final ColorPropertyManager colorManager_2dvs3d;
    protected final TexturePropertyManager textureManager_2dvs3d;
    protected final ContrastPropertyManager contrastManager_2dvs3d;
    protected TwoDVsThreeDTrialGenerator generator;
    protected long targetStimId;
    protected String textureType;
    protected RGBColor color;
    protected String targetSpecPath;
    protected ReceptiveField receptiveField;
    protected Long stimId;
    protected Coordinates2D imageCenterCoords = new Coordinates2D(0, 0);
    protected double contrast;

    /**
     *
     * @param generator
     * @param gaStimId: the stimulus id from the GA experiment we are changing the shading / color / contrast of for testing
     * @param textureType: "2D", "SHADE", "SPECULAR" or "USE_PARENT"
     * @param color
     * @param contrast: -1 means use the contrast from the GA experiment, otherwise, 0-1.
     */
    public TwoDVsThreeDStim(TwoDVsThreeDTrialGenerator generator, long gaStimId, String textureType, RGBColor color, Double contrast) {
        this.generator = generator;
        this.targetStimId = gaStimId;
        this.textureType = textureType;
        this.color = color;
        this.contrast = contrast;


        rfStrategyManager_ga = new RFStrategyPropertyManager(new JdbcTemplate(generator.gaDataSource));
        sizeManager_ga = new SizePropertyManager(new JdbcTemplate(generator.gaDataSource));
        colorManager_ga = new ColorPropertyManager(new JdbcTemplate(generator.gaDataSource));
        textureManager_ga = new TexturePropertyManager(new JdbcTemplate(generator.gaDataSource));
        contrastManager_ga = new ContrastPropertyManager(new JdbcTemplate(generator.gaDataSource));

        rfStrategyManager_2dvs3d = new RFStrategyPropertyManager(new JdbcTemplate(generator.getDbUtil().getDataSource()));
        sizeManager_2dvs3d = new SizePropertyManager(new JdbcTemplate(generator.getDbUtil().getDataSource()));
        colorManager_2dvs3d = new ColorPropertyManager(new JdbcTemplate(generator.getDbUtil().getDataSource()));
        textureManager_2dvs3d = new TexturePropertyManager(new JdbcTemplate(generator.getDbUtil().getDataSource()));
        contrastManager_2dvs3d = new ContrastPropertyManager(new JdbcTemplate(generator.getDbUtil().getDataSource()));

        rfStrategy = rfStrategyManager_ga.readProperty(gaStimId);
        sizeDiameterDegrees = sizeManager_ga.readProperty(gaStimId);

        targetSpecPath = generator.gaSpecPath + "/" + gaStimId + "_spec.xml";
        receptiveField = generator.rfSource.getReceptiveField();

        if (textureType.equals("USE_PARENT")){
            this.textureType = textureManager_ga.readProperty(gaStimId);
        }

        if (color == null) {
            this.color = colorManager_ga.readProperty(gaStimId);
        }

        if (contrast < 0) {
            System.out.println("Contrast is negative, using default contrast of 1.0");
            this.contrast = contrastManager_ga.readProperty(gaStimId);
        }
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        stimId = generator.getGlobalTimeUtil().currentTimeMicros();
        Point3d centerOfMass = getTargetsCenterOfMass();
        GAMatchStick mStick = new GAMatchStick(centerOfMass); //this constructor ignores RF for purposes of drawing
        mStick.setRf(receptiveField); //we need reference to this to calculate position for thumbnail
        mStick.setProperties(sizeDiameterDegrees, textureType, contrast);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(targetSpecPath, new double[]{0,0,0});
//
        saveMStickSpec(mStick);
        String pngPath = drawPng(mStick);
        drawThumbnails(mStick);
        AllenMStickData mStickData = (AllenMStickData) mStick.getMStickData();
        writeStimSpec(pngPath, mStickData);

        writeStimProperties();
    }

    protected Point3d getTargetsCenterOfMass() {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.gaDataSource);

        // Read the data XML from StimSpec table
        String dataXml = (String) jdbcTemplate.queryForObject(
                "SELECT data FROM StimSpec WHERE id = ?",
                new Object[]{targetStimId},
                String.class
        );

        if (dataXml == null || dataXml.isEmpty()) {
            throw new RuntimeException("No data found for stimId " + targetStimId + " in StimSpec table");
        }

        // Parse the XML into AllenMStickData
        AllenMStickData mStickData = (AllenMStickData) AllenMStickData.fromXml(dataXml);


        // Get center of mass
        Point3d centerOfMass = mStickData.getMassCenter();
        if (centerOfMass == null) {
            throw new RuntimeException("No center of mass found for stimId " + targetStimId + " in StimSpec table");
        }

        return centerOfMass;
    }

    protected void writeStimProperties() {
        colorManager_2dvs3d.writeProperty(stimId, color);
        textureManager_2dvs3d.writeProperty(stimId, textureType);
        sizeManager_2dvs3d.writeProperty(stimId, (float) sizeDiameterDegrees);
        rfStrategyManager_2dvs3d.writeProperty(stimId, rfStrategy);
        contrastManager_2dvs3d.writeProperty(stimId, contrast);
        writeStimGaId(this.targetStimId);
    }

    private void writeStimGaId(long targetStimId) {
        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.getDbUtil().getDataSource());

        jdbcTemplate.update(
                "INSERT INTO StimGaId (stim_id, ga_stim_id) VALUES (?, ?)",
                new Object[]{this.stimId,targetStimId}
        );
    }

    protected String drawPng(AllenMatchStick mStick) {
        //draw pngs
        List<String> labels = new LinkedList<>();
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);
        return pngPath;
    }

    protected void drawThumbnails(GAMatchStick mStick) {
        List<String> labels = new LinkedList<>();
        generator.getPngMaker().createAndSaveThumbnail(mStick, stimId, labels, generator.getGeneratorPngPath());
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

    protected void saveMStickSpec(GAMatchStick mStick) {
        AllenMStickSpec spec = new AllenMStickSpec();
        spec.setMStickInfo(mStick, true);
        spec.writeInfo2File(generator.getGeneratorSpecPath() + "/" + Long.toString(stimId), true);
    }

    @Override
    public Long getStimId() {
        return stimId;
    }
}