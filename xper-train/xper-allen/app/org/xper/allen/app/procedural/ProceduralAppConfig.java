package org.xper.allen.app.procedural;

import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.nafc.blockgen.procedural.EStimExperimentGenType;
import org.xper.allen.nafc.blockgen.procedural.NAFCTrialParamDbUtil;
import org.xper.allen.nafc.blockgen.procedural.NAFCBlockGen;
import org.xper.allen.nafc.blockgen.procedural.ProceduralRandGenType;
import org.xper.allen.nafc.experiment.juice.LinearControlPointFunction;
import org.xper.allen.nafc.experiment.juice.NAFCNoiseScalingNoiseController;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.allen.noisy.nafc.NoisyNAFCPngScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.FixationPoint;

import java.util.Arrays;
import java.util.List;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({NAFCMStickPngAppConfig.class, NAFCConfig.class})
public class ProceduralAppConfig {
    @Autowired
    public NAFCMStickPngAppConfig pngConfig;

    @Autowired
    public NAFCConfig nafcConfig;
    @ExternalValue("generator.noisemap_path")
    public String generatorNoiseMapPath;

    @ExternalValue("experiment.noisemap_path")
    public String experimentNoiseMapPath;

    @ExternalValue("ga.spec_path")
    public String gaSpecPath;

    @Bean
    public NoisyNAFCPngScene taskScene() {
        NoisyNAFCPngScene scene = new NoisyNAFCPngScene();
        scene.setRenderer(pngConfig.config.experimentGLRenderer());
        scene.setFixation(experimentFixationPoint());
        scene.setMarker(nafcConfig.screenMarker());
        scene.setBlankScreen(new BlankScreen());
        scene.setScreenHeight(pngConfig.classicConfig.xperMonkeyScreenHeight());
        scene.setScreenWidth(pngConfig.classicConfig.xperMonkeyScreenWidth());
        scene.setDistance(pngConfig.classicConfig.xperMonkeyScreenDistance());
        scene.setBackgroundColor(pngConfig.classicConfig.xperBackgroundColor());
        scene.setFrameRate(pngConfig.mStickPngConfig.xperNoiseRate());
        return scene;
    }
    @Bean
    public FixationPoint experimentFixationPoint() {
        FixationPoint f = new FixationPoint();
        f.setColor(pngConfig.classicConfig.xperFixationPointColor());
        f.setFixationPosition(pngConfig.classicConfig.xperFixationPosition());
        f.setSize(pngConfig.classicConfig.xperFixationPointSize());
        return f;
    }

    @Bean
    public NAFCTrialGeneratorGUI nafcTrialGeneratorGUI() {
        NAFCTrialGeneratorGUI gui = new NAFCTrialGeneratorGUI();
        gui.setBlockgen(blockGen());
        gui.setStimTypes(Arrays.asList(
                proceduralRandGenType(),
                getEStimExperimentGenType()
        ));
        gui.setDefaultStimType(proceduralRandGenType());
        return gui;
    }

    @Bean
    public ProceduralRandGenType proceduralRandGenType() {
        return new ProceduralRandGenType(blockGen());
    }

    @Bean
    public EStimExperimentGenType getEStimExperimentGenType() {
        EStimExperimentGenType eStimExperimentGenType = new EStimExperimentGenType();
        eStimExperimentGenType.setGaSpecPath(gaSpecPath);
        eStimExperimentGenType.setGenerator(blockGen());
        return eStimExperimentGenType;
    }

    @Bean
    public NAFCBlockGen blockGen() {
        NAFCBlockGen blockGen = new NAFCBlockGen();
        //Dependencies of superclasses
        blockGen.setDbUtil(pngConfig.config.allenDbUtil());
        blockGen.setGlobalTimeUtil(pngConfig.acqConfig.timeClient());
        blockGen.setGeneratorPngPath(pngConfig.mStickPngConfig.generatorPngPath);
        blockGen.setExperimentPngPath(pngConfig.mStickPngConfig.experimentPngPath);
        blockGen.setGeneratorSpecPath(pngConfig.mStickPngConfig.generatorSpecPath);
        blockGen.setPngMaker(pngConfig.mStickPngConfig.pngMaker());
        blockGen.setImageDimensionDegrees(pngConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
        //Dependencies of ProceduuralExperimentBlockGen
        blockGen.setGeneratorNoiseMapPath(generatorNoiseMapPath);
        blockGen.setExperimentNoiseMapPath(experimentNoiseMapPath);
        blockGen.setNafcTrialDbUtil(nafcTrialDbUtil());
        return blockGen;
    }

    @Bean
    public NAFCTrialParamDbUtil nafcTrialDbUtil() {
        NAFCTrialParamDbUtil nafcTrialDbUtil = new NAFCTrialParamDbUtil();
        nafcTrialDbUtil.setDataSource(pngConfig.config.dataSource());
        return nafcTrialDbUtil;
    }

    @Bean
    public ChoiceEventListener juiceController(){
        NAFCNoiseScalingNoiseController controller = new NAFCNoiseScalingNoiseController();
        controller.setJuice(pngConfig.classicConfig.xperDynamicJuice());
        controller.setNoiseRewardFunction(noiseRewardFunction());
        return controller;
    }

    @Bean
    public UnivariateRealFunction noiseRewardFunction() {
        LinearControlPointFunction function = new LinearControlPointFunction();
        function.setxValues(xperNoiseRewardFunctionNoises());
        function.setyValues(xperNoiseRewardFunctionRewards());
        return function;
    }

//    @Bean
//    public List<Double> xperNoiseRewardFunctionNoises() {
//        return Arrays.asList(0.0, 0.2, 0.3, 0.5, 1.0);
//    }

//    @Bean
//    public List<Double> xperNoiseRewardFunctionRewards() {
//        return Arrays.asList(1.5, 1.5, 2.5, 3.3, 4.5);
//    }

    @Bean
    public List<Double> xperNoiseRewardFunctionNoises() {
        return Arrays.asList(0.0, 0.1, 0.3, 0.4, 0.5, 1.0);
    }


    @Bean
    public List<Double> xperNoiseRewardFunctionRewards() {
        return Arrays.asList(1.0, 2.5, 3.5, 4.0, 4.5, 6.0);
    }
}