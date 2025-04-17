package org.xper.allen.pga;

import org.springframework.jdbc.core.JdbcTemplate;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.morph.MorphData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.stimproperty.*;
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
    protected RFStrategy rfStrategy;

    protected final ContrastPropertyManager contrastManager;
    protected final ColorPropertyManager colorManager;
    protected   final TexturePropertyManager textureManager;
    protected final SizePropertyManager sizeManager;
    protected final RFStrategyPropertyManager rfStrategyManager;
    protected final UnderlyingTexturePropertyManager underlyingTextureManager;

    protected Long stimId;
    protected String textureType;
    protected RGBColor color;
    protected double sizeDiameterDegrees;
    protected double contrast;
    private T mStick;
    // For swapping between 2D/3D textures with preserved average contrast
    protected boolean useAverageContrast;
    protected boolean is2d;
    protected String underlyingTexture;

    /**
     * Original constructor, deprecated
     *
     * @param stimId
     * @param generator
     * @param parentId
     * @param textureType
     * @param useAverageContrast
     */
    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, String textureType, boolean useAverageContrast) {
        this.generator = generator;
        this.parentId = parentId;
        this.imageCenterCoords = new Coordinates2D(0, 0);
        this.stimId = stimId;
        this.textureType = textureType;
        this.useAverageContrast = useAverageContrast;

        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.getDbUtil().getDataSource());
        colorManager = new ColorPropertyManager(jdbcTemplate);
        textureManager = new TexturePropertyManager(jdbcTemplate);
        sizeManager = new SizePropertyManager(jdbcTemplate);
        rfStrategyManager = new RFStrategyPropertyManager(jdbcTemplate);
        contrastManager = new ContrastPropertyManager(jdbcTemplate);
        underlyingTextureManager = new UnderlyingTexturePropertyManager(jdbcTemplate);
    }

    /**
     * Constructor for SideTest
     * @param stimId
     * @param generator
     * @param parentId
     */
    public GAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId) {
        this.generator = generator;
        this.parentId = parentId;
        this.imageCenterCoords = new Coordinates2D(0, 0);
        this.stimId = stimId;
        this.useAverageContrast = true;

        JdbcTemplate jdbcTemplate = new JdbcTemplate(generator.getDbUtil().getDataSource());
        colorManager = new ColorPropertyManager(jdbcTemplate);
        textureManager = new TexturePropertyManager(jdbcTemplate);
        sizeManager = new SizePropertyManager(jdbcTemplate);
        rfStrategyManager = new RFStrategyPropertyManager(jdbcTemplate);
        contrastManager = new ContrastPropertyManager(jdbcTemplate);
        underlyingTextureManager = new UnderlyingTexturePropertyManager(jdbcTemplate);
    }

    @Override
    public void preWrite() {

    }

    @Override
    public void writeStim() {
        int nTries = 0;
        mStick = null;
        int maxTries = 100;
        while(nTries < maxTries) {
            nTries++;
            try {
                setProperties();
                if (!useAverageContrast) {
                    mStick = createMStick();
                } else {
                    //weird hack to get around that we have to draw something 3D first to get the average contrast
                    String originalTextureType = textureType;
                    boolean originalDness = is2d;
                    textureType = underlyingTexture;


                    is2d = false;
                    mStick = createMStick(); //Make 3D version
                    AllenMStickSpec mStickSpec = new AllenMStickSpec();
                    mStickSpec.setMStickInfo(mStick, false);

                    contrast = generator.getPngMaker().getWindow().calculateAverageContrast(mStick);

                    textureType = originalTextureType;
                    is2d = originalDness;
                    mStick = (T) new GAMatchStick(mStick.getMassCenter());
                    mStick.setRf(generator.getReceptiveField());
                    mStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
                    mStick.setStimColor(color);
                    mStick.genMatchStickFromShapeSpec(mStickSpec, new double[]{0.0,0.0,0.0});

                }

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
        drawCompMaps(mStick);
        String pngPath = drawPngs(mStick);
        drawThumbnails(mStick);

        D mStickData = (D) mStick.getMStickData();
        writeStimSpec(pngPath, mStickData);

        writeStimProperties();

        writeMorphData(mStick);
    }


    protected void writeMorphData(T mStick) {
        MorphData morphData = mStick.getMorphData();
        String morphDataXml = morphData.toXml();
        JdbcTemplate jt = new JdbcTemplate(generator.getDbUtil().getDataSource());
        jt.update("insert into StimMorphData (stim_id, data) values (?, ?)",
                new Object[] { stimId, morphDataXml });
    }

    protected void setProperties(){
        chooseRFStrategy(); //must be first otherwise chooseSize may fail
        chooseSize();
        chooseTextureType();
        chooseColor();
        chooseUnderlyingTexture();
        chooseContrast();

        if (rfStrategy == null) {
            throw new IllegalArgumentException("RF Strategy cannot be null");
        }
        if (textureType == null) {
            throw new IllegalArgumentException("Texture Type cannot be null");
        }
        if (color == null) {
            throw new IllegalArgumentException("Color cannot be null");
        }
        if (sizeDiameterDegrees == 0) {
            throw new IllegalArgumentException("Size cannot be 0");
        }
    }

    protected abstract void chooseRFStrategy();

    protected void chooseColor() {
        color = colorManager.readProperty(parentId);
    }

    protected void chooseUnderlyingTexture() {
        if (is2d){
            this.underlyingTexture = underlyingTextureManager.readProperty(parentId);
        } else{
            this.underlyingTexture = textureType; //not needed to draw in this 3d case, but we want to pass this along in genetic info
        }
    }

    protected void chooseContrast() {
        contrast = contrastManager.readProperty(parentId);
    }

    public static boolean is2D(String textureType) {
        return textureType.equals("2D");
    }

    public static boolean is3D(String texture) {
        return texture.equals("SHADE") || texture.equals("SPECULAR");
    }

    protected abstract void chooseSize();

    /**
     * For properties not specified by MStickSpec, but matter for what the stim looks like.
     */
    protected void writeStimProperties() {
        colorManager.writeProperty(stimId, color);
        textureManager.writeProperty(stimId, textureType);
        sizeManager.writeProperty(stimId, (float) sizeDiameterDegrees);
        rfStrategyManager.writeProperty(stimId, rfStrategy);
        contrastManager.writeProperty(stimId, contrast);
        underlyingTextureManager.writeProperty(stimId, underlyingTexture);

    }

    protected T createRandMStick() {
        GAMatchStick mStick = new GAMatchStick(generator.getReceptiveField(), rfStrategy);
        mStick.setProperties(RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees()), textureType, 1.0);
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
        String pngPath = generator.getPngMaker().createAndSavePNG(mStick, stimId, labels, generator.getGeneratorPngPath());
        pngPath = generator.convertPngPathToExperiment(pngPath);
        return pngPath;
    }

    protected void drawThumbnails(T mStick) {
        List<String> labels = new LinkedList<>();
        generator.getPngMaker().createAndSaveThumbnail(mStick, stimId, labels, generator.getGeneratorPngPath());
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

    protected void chooseTextureType() {
        switch (textureType){
            case "2D":
                textureType = "2D";
                is2d = true;
                break;
            case "3D":
                textureType = Math.random() < 0.5 ? "SHADE" : "SPECULAR";
                is2d = false;
                break;
            case "SHADE":
                textureType = "SHADE";
                is2d = false;
                break;
            case "SPECULAR":
                textureType = "SPECULAR";
                is2d = false;
                break;
            default:
                throw new IllegalArgumentException("Invalid texture type: " + textureType);

        }
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