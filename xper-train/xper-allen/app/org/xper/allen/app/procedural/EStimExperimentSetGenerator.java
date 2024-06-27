package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenMatchStick;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.drawing.RGBColor;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.util.Collections;

public class EStimExperimentSetGenerator {

    @Dependency
    private EStimExperimentTrialGenerator generator;

    @Dependency
    String generatorSetPath;

    public static void main(String[] args) {
        try {
            UIManager.setLookAndFeel(UIManager.getSystemLookAndFeelClassName());
        } catch (Exception e) {
            throw new XGLException(e);
        }

        JavaConfigApplicationContext context = new JavaConfigApplicationContext(
                FileUtil.loadConfigClass("experiment.config_class"));
        EStimExperimentSetGenerator setGenerator = context.getBean(EStimExperimentSetGenerator.class);
        setGenerator.generateSet();
    }

    /**
     * I: first out of noise + hypothesis in noise component
     * II: morphed out of noise + hypothesis in noise component
     * III: first out of noise + morphed in noise component
     */
    public void generateSet() {
        long stimId = 1717531847396095L;
        int compId = 2;

        //Initializing Drawing Stuff
        AllenPNGMaker pngMaker = generator.getPngMaker();
        pngMaker.createDrawerWindow();

        EStimShapeTwoByTwoMatchStick baseMStick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        double maxSizeDiameterDegreesFromRF = RFUtils.calculateMStickMaxSizeDiameterDegrees(RFStrategy.PARTIALLY_INSIDE, generator.getRfSource());
        baseMStick.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        baseMStick.setStimColor(new RGBColor(0.5, 0.5, 0.5));
        baseMStick.genMatchStickFromFile(generator.getGaSpecPath() + "/" + stimId + "_spec.xml");

        EStimShapeTwoByTwoMatchStick stick1 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        AllenMStickSpec stick1Spec = new AllenMStickSpec();
        stick1.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick1.setStimColor(new RGBColor(0.5, 0.5, 0.5));
        stick1.genMatchStickFromComponentInNoise(baseMStick,
                compId,
                0,
                true);
        stick1Spec.setMStickInfo(stick1, true);
        stick1Spec.writeInfo2File(
                generatorSetPath + "/"
                        + stimId + "_"
                        + compId + "_"
                        + "I"
                        + "_spec.xml");
        pngMaker.createAndSavePNG(stick1,
                stimId,
                Collections.singletonList("I"),
                generatorSetPath
                );

        EStimShapeTwoByTwoMatchStick stick2 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        AllenMStickSpec stick2Spec = new AllenMStickSpec();
        stick2.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick2.setStimColor(new RGBColor(0.5, 0.5, 0.5));
        stick2.genMorphedBaseMatchStick(
                stick1,
                stick1.getDrivingComponent(),
                100,
                true,
                true);
        stick2Spec.setMStickInfo(stick2, true);
        stick2Spec.writeInfo2File(
                generatorSetPath + "/"
                        + stimId + "_"
                        + compId + "_"
                        + "II"
                        + "_spec.xml");
        pngMaker.createAndSavePNG(stick2,
                stimId,
                Collections.singletonList("II"),
                generatorSetPath
        );


        EStimShapeTwoByTwoMatchStick stick3 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        AllenMStickSpec stick3Spec = new AllenMStickSpec();
        stick3.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick3.genMorphedDrivingComponentMatchStick(
                stick1,
                0.7,
                1.0/3.0,
                true,
                true);
        stick3Spec.setMStickInfo(stick3, true);
        stick3Spec.writeInfo2File(
                generatorSetPath + "/"
                        + stimId + "_"
                        + compId + "_"
                        + "III"
                        + "_spec.xml");
        pngMaker.createAndSavePNG(stick3,
                stimId,
                Collections.singletonList("III"),
                generatorSetPath
        );

        EStimShapeTwoByTwoMatchStick stick4 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        AllenMStickSpec stick4Spec = new AllenMStickSpec();
        stick4.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick4.genSwappedBaseAndDrivingComponentMatchStick(
                stick2,
                stick2.getDrivingComponent(),
                stick3,
                true
        );
        stick4Spec.setMStickInfo(stick4, true);
        stick4Spec.writeInfo2File(
                generatorSetPath + "/"
                        + stimId + "_"
                        + compId + "_"
                        + "IV"
                        + "_spec.xml");
        pngMaker.createAndSavePNG(stick4,
                stimId,
                Collections.singletonList("IV"),
                generatorSetPath
        );
        pngMaker.close();
    }



    public EStimExperimentTrialGenerator getGenerator() {
        return generator;
    }

    public void setGenerator(EStimExperimentTrialGenerator generator) {
        this.generator = generator;
    }

    public String getGeneratorSetPath() {
        return generatorSetPath;
    }

    public void setGeneratorSetPath(String generatorSetPath) {
        this.generatorSetPath = generatorSetPath;
    }
}