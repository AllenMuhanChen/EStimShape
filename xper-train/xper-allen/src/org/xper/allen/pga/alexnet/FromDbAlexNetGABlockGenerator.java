package org.xper.allen.pga.alexnet;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.allen.pga.StimGaInfoEntry;

import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

import java.io.FileInputStream;
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
    AlexNetDrawingManager drawingManager;


    private RGBColor color;

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

        //Handle input
        int r = Integer.parseInt(args[0]);
        int g = Integer.parseInt(args[1]);
        int b = Integer.parseInt(args[2]);
        generator.color = new RGBColor(r/255f,g/255f,b/255f);

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
                float[] lightingDirection = {500.0f, 0.0f, 0.0f, 1.0f};

                Stim stim;
                switch (stimType) {
                    case SEEDING:
                        stim = new SeedingStim(this, parentId, stimId, textureType, color, lightingDirection);
                        break;
                    case RF_LOCATE:
                        stim = new RFLocStim(this, parentId, stimId, textureType, color, lightingDirection, magnitude);
                        break;
                    case GROWING:
                        stim = new GrowingStim(this, parentId, stimId, textureType, color, lightingDirection, magnitude);
                        break;
                    default:
                        throw new IllegalArgumentException("No enum constant found for value: " + stimInfo.getStimType());
                }

                stims.add(stim);

            } catch (Exception e) {
                e.printStackTrace();
            }
        }

    }

    //We don't need TaskToDo in here
    protected void writeTrials() {
        for (Stim stim : getStims()) {
            stim.writeStim();
        }
    }

    protected void init(){
        drawingManager.createDrawerWindow();
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

    public AlexNetDrawingManager getDrawingManager() {
        return drawingManager;
    }

    public void setDrawingManager(AlexNetDrawingManager drawingManager) {
        this.drawingManager = drawingManager;
    }
}