package org.xper.allen.pga.alexnet;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.allen.Stim;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.allen.pga.alexnet.SeedingStim;
import org.xper.allen.pga.StimGaInfoEntry;

import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.List;
import java.util.Properties;

public class FromDbAlexNetGABlockGenerator extends AbstractTrialGenerator<Stim> {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    String gaName;

    @Dependency
    protected String generatorPngPath;

    @Dependency
    protected String experimentPngPath;

    @Dependency
    protected String generatorSpecPath;

    @Dependency
    AllenPNGMaker pngMaker;

    public static void main(String[] args) throws IOException, ClassNotFoundException {
        // Load the properties file
        Properties props = new Properties();
        props.load(new FileInputStream("/home/r2_allen/git/EStimShape/xper-train/xper-allen/app/xper.properties.alexnet"));

        // Set as system properties
        Properties sysProps = System.getProperties();
        sysProps.putAll(props);
        System.setProperties(sysProps);

        // Get the config class and create context
        Class<?> configClass = Class.forName(props.getProperty("experiment.ga.config_class"));
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(configClass);

        // Get and run generator
        FromDbAlexNetGABlockGenerator generator = context.getBean(FromDbAlexNetGABlockGenerator.class);
        generator.generate();
    }

    @Override
    protected void addTrials() {
        Long experimentId = dbUtil.readCurrentExperimentId(gaName);
        List<Long> lineageIdsInThisExperiment = dbUtil.readLineageIdsForExperiment(experimentId);
        List<Long> stimIdsToGenerate = dbUtil.findStimIdsWithoutStimSpec(lineageIdsInThisExperiment);

        for (Long stimId : stimIdsToGenerate) {
            StimGaInfoEntry stimInfo = dbUtil.readStimGaInfoEntry(stimId);
            double magnitude = stimInfo.getMutationMagnitude();
            Long parentId = stimInfo.getParentId();

            try{
                StimType stimType;
                stimType = StimType.valueOf(stimInfo.getStimType());

                String textureType = "SHADE";
                RGBColor color = new RGBColor(0, 0, 0);
                Coordinates2D location = new Coordinates2D(0, 0);
                float[] lightingDirection = {0, 0, 0};
                double sizeDiameter = 0.0;

                Stim stim;
                switch (stimType) {
                    case SEEDING:
                        stim = new SeedingStim(this, parentId, stimId, textureType, color, location, lightingDirection, sizeDiameter);
                        break;
//                    case RF_LOCATE:
//                        stim = new RFStim(stimId, this, new Coordinates2D(0, 0), "SHADE", new RGBColor(0, 0, 0), RFStrategy.PARTIALLY_INSIDE);
//                        break;
//                    case GROWING:
//                        stim = new GrowingStim(stimId, this, new Coordinates2D(0, 0), "SHADE", new RGBColor(0, 0, 0), RFStrategy.PARTIALLY_INSIDE);
//                        break;
                    default:
                        throw new IllegalArgumentException("No enum constant found for value: " + stimInfo.getStimType());
                }

                stims.add(stim);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

    }

    protected void init(){
        getPngMaker().createDrawerWindow();
    }

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public String getGaName() {
        return gaName;
    }

    public void setGaName(String gaName) {
        this.gaName = gaName;
    }

    public String getGeneratorPngPath() {
        return generatorPngPath;
    }

    public void setGeneratorPngPath(String generatorPngPath) {
        this.generatorPngPath = generatorPngPath;
    }

    public String getExperimentPngPath() {
        return experimentPngPath;
    }

    public void setExperimentPngPath(String experimentPngPath) {
        this.experimentPngPath = experimentPngPath;
    }

    public String getGeneratorSpecPath() {
        return generatorSpecPath;
    }

    public void setGeneratorSpecPath(String generatorSpecPath) {
        this.generatorSpecPath = generatorSpecPath;
    }

    public AllenPNGMaker getPngMaker() {
        return pngMaker;
    }

    public void setPngMaker(AllenPNGMaker pngMaker) {
        this.pngMaker = pngMaker;
    }
}