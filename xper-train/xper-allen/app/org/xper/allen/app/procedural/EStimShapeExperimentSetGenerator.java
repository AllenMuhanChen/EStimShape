package org.xper.allen.app.procedural;

import org.springframework.config.java.context.JavaConfigApplicationContext;
import org.xper.Dependency;
import org.xper.allen.app.estimshape.EStimShapeExperimentTrialGenerator;
import org.xper.allen.drawing.composition.AllenMStickSpec;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.drawing.composition.experiment.EStimShapeTwoByTwoMatchStick;
import org.xper.allen.drawing.composition.experiment.ProceduralMatchStick;
import org.xper.allen.drawing.composition.experiment.TwoByTwoMatchStick;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.composition.noisy.NoiseMapper;
import org.xper.allen.nafc.blockgen.estimshape.StickProvider;
import org.xper.allen.pga.RFStrategy;
import org.xper.allen.pga.RFUtils;
import org.xper.exception.XGLException;
import org.xper.util.FileUtil;

import javax.swing.*;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

import static org.xper.allen.nafc.blockgen.MStickGenerationUtils.attemptMorph;

public class EStimShapeExperimentSetGenerator {

    @Dependency
    private EStimShapeExperimentTrialGenerator generator;

    @Dependency
    String generatorSetPath;

    @Dependency
    NoiseMapper noiseMapper;

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
        EStimShapeExperimentSetGenerator setGenerator = context.getBean(EStimShapeExperimentSetGenerator.class);
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
        long stimId = 1717531847398316L;
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
//                EStimShapeTwoByTwoMatchStick stick2 = makeStickI(baseMStick, compId);
                saveSpec(stick2, stimId, compId, "II");
                savePng(stick2, stimId, "II");

                EStimShapeTwoByTwoMatchStick stick3 = makeStickIII(stick1);
                saveSpec(stick3, stimId, compId, "III");
                savePng(stick3, stimId, "III");

                EStimShapeTwoByTwoMatchStick stick4 = makeStickIV(stick2, stick3);
                saveSpec(stick4, stimId, compId, "IV");
                savePng(stick4, stimId, "IV");
            } catch(MorphedMatchStick.MorphException me) {
                System.out.println("Failed Morph: because of reason");
                System.err.println(me.getMessage());
                continue;

            }
            catch (Exception e){
                e.printStackTrace();
                continue;
            }

            break;
        }

        pngMaker.close();
    }

    private EStimShapeTwoByTwoMatchStick loadBaseMStick(long stimId) {
        EStimShapeTwoByTwoMatchStick baseMStick = new EStimShapeTwoByTwoMatchStick(
                RFStrategy.PARTIALLY_INSIDE,
                generator.getRF(),
                noiseMapper);
        maxSizeDiameterDegreesFromRF = RFUtils.calculateMStickMaxSizeDiameterDegrees(
                RFStrategy.PARTIALLY_INSIDE, generator.getRfSource().getRFRadiusDegrees());
        baseMStick.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
        baseMStick.genMatchStickFromFile(generator.getGaSpecPath() + "/" + stimId + "_spec.xml");
        return baseMStick;
    }

    private EStimShapeTwoByTwoMatchStick makeStickI(EStimShapeTwoByTwoMatchStick baseMStick, int compId) {
        return attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                EStimShapeTwoByTwoMatchStick stick1 = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                stick1.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
                stick1.genMatchStickFromComponentInNoise(baseMStick,
                        compId,
                        nComp,
                        true, stick1.maxAttempts, noiseMapper);
                stick1.setMaxAttempts(15);

                List<Integer> deltaCompsToNoise = identifyCompsToNoise(stick1, true);
                noiseMapper.checkInNoise(stick1, deltaCompsToNoise, 0.5);
                return stick1;
            }
        }, 15);

    }

    private EStimShapeTwoByTwoMatchStick makeStickII(EStimShapeTwoByTwoMatchStick stick1) {
        return attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                System.out.println("WORKING ON II");
                EStimShapeTwoByTwoMatchStick stick2 = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                stick2.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
                stick2.genMorphedBaseMatchStick(
                        stick1,
                        stick1.getDrivingComponent(),
                        15,
                        true,
                        true
                );
                List<Integer> deltaCompsToNoise = identifyCompsToNoise(stick2, true);
                noiseMapper.checkInNoise(stick2, deltaCompsToNoise, 0.5);
                return stick2;
            }
        }, 15);

    }

    private EStimShapeTwoByTwoMatchStick makeStickIII(EStimShapeTwoByTwoMatchStick stick1) {
        return attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                System.out.println("WORKING ON III");
                EStimShapeTwoByTwoMatchStick stick3 = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                stick3.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
                stick3.genMorphedDrivingComponentMatchStick(
                        stick1,
                        0.6,
                        1.0/3.0,
                        true,
                        true, stick1.maxAttempts);
                List<Integer> deltaCompsToNoise = identifyCompsToNoise(stick3, true);
                noiseMapper.checkInNoise(stick3, deltaCompsToNoise, 0.5);
                return stick3;
            }
        }, 15);
    }

    private EStimShapeTwoByTwoMatchStick makeStickIV(EStimShapeTwoByTwoMatchStick stick2, EStimShapeTwoByTwoMatchStick stick3) {
        return attemptMorph(new StickProvider<EStimShapeTwoByTwoMatchStick>() {
            @Override
            public EStimShapeTwoByTwoMatchStick makeStick() {
                System.out.println("WORKING ON IV");
                EStimShapeTwoByTwoMatchStick stick4 = new EStimShapeTwoByTwoMatchStick(
                        RFStrategy.PARTIALLY_INSIDE,
                        generator.getRF(),
                        noiseMapper);
                stick4.setProperties(maxSizeDiameterDegreesFromRF, "SHADE");
                stick4.genSwappedBaseAndDrivingComponentMatchStick(
                        stick2,
                        stick2.getDrivingComponent(),
                        stick3,
                        true, 15
                );
                List<Integer> deltaCompsToNoise = identifyCompsToNoise(stick4, true);
                noiseMapper.checkInNoise(stick4, deltaCompsToNoise, 0.5);
                return stick4;
            }
        }, 15);
    }

    protected List<Integer> identifyCompsToNoise(ProceduralMatchStick sample, boolean isDeltaNoise) {
        List<Integer> compIdsToNoise = new ArrayList<>();
        if (!isDeltaNoise) {
            compIdsToNoise.add(sample.getDrivingComponent());
        } else {
            for (int compId = 1; compId <= sample.getnComponent(); compId++) {
                if (compId != sample.getDrivingComponent()) {
                    compIdsToNoise.add(compId);
                }
            }
        }
        return compIdsToNoise;
    }

    private void savePng(EStimShapeTwoByTwoMatchStick stick, long stimId, String type) {
        TwoByTwoMatchStick stickToDraw = new TwoByTwoMatchStick(noiseMapper);
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
        stick4Spec.setMStickInfo(stick4, false);
        stick4Spec.writeInfo2File(
                generatorSetPath + "/"
                        + stimId + "_"
                        + compId + "_"
                        + type
                        , false);
    }

    public EStimShapeExperimentTrialGenerator getGenerator() {
        return generator;
    }

    public void setGenerator(EStimShapeExperimentTrialGenerator generator) {
        this.generator = generator;
    }

    public String getGeneratorSetPath() {
        return generatorSetPath;
    }

    public void setGeneratorSetPath(String generatorSetPath) {
        this.generatorSetPath = generatorSetPath;
    }

    public NoiseMapper getNoiseMapper() {
        return noiseMapper;
    }

    public void setNoiseMapper(NoiseMapper noiseMapper) {
        this.noiseMapper = noiseMapper;
    }
}