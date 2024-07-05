package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.TwobyTwoMatchStick;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.util.Collections;
import java.util.LinkedList;

public class EStimExperimentSetGenerator {

    @Dependency
    private EStimExperimentTrialGenerator generator;

    @Dependency
    String generatorSetPath;

    private AllenPNGMaker pngMaker;
    private double maxSizeDiameterDegreesFromRF;
    private int nComp;

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
     * IV: morphed out of noise + morphed in noise component
     */
    public void generateSet() {
        //PARAMETERS
//        long stimId = 1717531847396095L;
        long stimId = 1717531847374356L;
        int compId = 2;
        nComp = 2;


        pngMaker = generator.getPngMaker();

        pngMaker.createDrawerWindow();

        EStimShapeTwoByTwoMatchStick baseMStick = loadBaseMStick(stimId);

        while (true) {
            try {
                EStimShapeTwoByTwoMatchStick stick1 = makeStickI(baseMStick, compId);
                saveSpec(stick1, stimId, compId, "I");
                savePng(stick1, stimId, "I");
                EStimShapeTwoByTwoMatchStick stick2 = makeStickII(stick1);
                saveSpec(stick2, stimId, compId, "II");
                savePng(stick2, stimId, "II");

                EStimShapeTwoByTwoMatchStick stick3 = makeStickIII(stick1);
                saveSpec(stick3, stimId, compId, "III");
                savePng(stick3, stimId, "III");

                EStimShapeTwoByTwoMatchStick stick4 = makeStickIV(stick2, stick3);
                saveSpec(stick4, stimId, compId, "IV");
                savePng(stick4, stimId, "IV");
            } catch (Exception e){
                System.out.println(e.getMessage());
                continue;
            }

            break;
        }

        pngMaker.close();
    }

    private EStimShapeTwoByTwoMatchStick loadBaseMStick(long stimId) {
        EStimShapeTwoByTwoMatchStick baseMStick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        maxSizeDiameterDegreesFromRF = RFUtils.calculateMStickMaxSizeDiameterDegrees(
                RFStrategy.PARTIALLY_INSIDE, generator.getRfSource());
        baseMStick.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        baseMStick.genMatchStickFromFile(generator.getGaSpecPath() + "/" + stimId + "_spec.xml");
        return baseMStick;
    }

    private EStimShapeTwoByTwoMatchStick makeStickI(EStimShapeTwoByTwoMatchStick baseMStick, int compId) {
        EStimShapeTwoByTwoMatchStick stick1 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        stick1.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick1.genMatchStickFromComponentInNoise(baseMStick,
                compId,
                nComp,
                true);

        return stick1;
    }

    private EStimShapeTwoByTwoMatchStick makeStickII(EStimShapeTwoByTwoMatchStick stick1) {
        EStimShapeTwoByTwoMatchStick stick2 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        stick2.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick2.genMorphedBaseMatchStick(
                stick1,
                stick1.getDrivingComponent(),
                100,
                true,
                true,
                0.5,
                1 / 2.0);
        return stick2;
    }

    private EStimShapeTwoByTwoMatchStick makeStickIII(EStimShapeTwoByTwoMatchStick stick1) {
        EStimShapeTwoByTwoMatchStick stick3 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        stick3.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick3.genMorphedDrivingComponentMatchStick(
                stick1,
                0.5,
                1.0/2.0,
                true,
                true);
        return stick3;
    }

    private EStimShapeTwoByTwoMatchStick makeStickIV(EStimShapeTwoByTwoMatchStick stick2, EStimShapeTwoByTwoMatchStick stick3) {
        EStimShapeTwoByTwoMatchStick stick4 = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF()
        );
        stick4.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        stick4.genSwappedBaseAndDrivingComponentMatchStick(
                stick2,
                stick2.getDrivingComponent(),
                stick3,
                true
        );
        return stick4;
    }

    private void savePng(EStimShapeTwoByTwoMatchStick stick, long stimId, String type) {
        TwobyTwoMatchStick stickToDraw = new TwobyTwoMatchStick();
        stickToDraw.setProperties(generator.getImageDimensionsDegrees(), "SHADE");
        AllenMStickSpec stickSpec = new AllenMStickSpec();
        stickSpec.setMStickInfo(stick, true);
        stickToDraw.genMatchStickFromShapeSpec(stickSpec, new double[]{0,0,0});
        stickToDraw.centerShape();
        pngMaker.createAndSavePNG(stickToDraw,
                stimId,
                Collections.singletonList(type),
                generatorSetPath
        );
        LinkedList<String> labels = new LinkedList<>();
        labels.add(type);
        pngMaker.createAndSaveCompMap(stickToDraw,
                stimId,
                labels,
                generatorSetPath
        );
    }

    private void saveSpec(EStimShapeTwoByTwoMatchStick stick4, long stimId, int compId, String type) {
        AllenMStickSpec stick4Spec = new AllenMStickSpec();
        stick4Spec.setMStickInfo(stick4, true);
        stick4Spec.writeInfo2File(
                generatorSetPath + "/"
                        + stimId + "_"
                        + compId + "_"
                        + type
                        );
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