package org.xper.allen.pga.alexnet.lightingposthoc;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.allen.pga.alexnet.AlexNetDrawingManager;
import org.xper.allen.pga.alexnet.FromDbAlexNetGABlockGenerator;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.drawing.RGBColor;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.Properties;

public class LightingPostHocGenerator extends AbstractTrialGenerator<Stim> {
    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    protected String generatorPngPath;

    @Dependency
    protected String generatorSpecPath;

    @Dependency
    AlexNetDrawingManager drawingManager;

    public static void main(String[] args) throws IOException, ClassNotFoundException {
        // Load the properties file
        Properties props = new Properties();
        props.load(new FileInputStream("/home/r2_allen/git/EStimShape/xper-train/shellScripts/xper.properties.alexnet.lightingposthoc"));

        // Set as system properties
        Properties sysProps = System.getProperties();
        sysProps.putAll(props);
        System.setProperties(sysProps);

        // Get the config class and create context
        Class<?> configClass = Class.forName(props.getProperty("experiment.ga.config_class"));
        JavaConfigApplicationContext context = new JavaConfigApplicationContext(configClass);

        // Get and run generator
        LightingPostHocGenerator generator = context.getBean(LightingPostHocGenerator.class);

        generator.generate();
    }
    @Override
    protected void addTrials() {
        //read StimInstruction

        //check if stim has an entry in StimPath

        //if not:

        //if type is TEXTURE_3D_VARIATION
            //Generate stimuli using instructions and save to StimSpec and StimPath

        //if type is 2D
            // Generate using new contrast and 2D instructions


    }

    @Override
    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public String getGeneratorPngPath() {
        return generatorPngPath;
    }

    public void setGeneratorPngPath(String generatorPngPath) {
        this.generatorPngPath = generatorPngPath;
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