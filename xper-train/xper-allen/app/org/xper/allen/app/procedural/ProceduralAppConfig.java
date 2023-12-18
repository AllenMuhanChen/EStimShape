package org.xper.allen.app.procedural;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.config.NAFCConfig;
import org.xper.allen.nafc.blockgen.procedural.NAFCTrialParamDbUtil;
import org.xper.allen.nafc.blockgen.procedural.ProceduralExperimentBlockGen;
import org.xper.allen.noisy.nafc.NoisyNAFCPngScene;
import org.xper.drawing.object.BlankScreen;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({NAFCMStickPngAppConfig.class, NAFCConfig.class})
public class ProceduralAppConfig {
    @Autowired
    public NAFCMStickPngAppConfig pngConfig;

    @ExternalValue("generator.noisemap_path")
    public String generatorNoiseMapPath;

    @ExternalValue("experiment.noisemap_path")
    public String experimentNoiseMapPath;

    @Bean
    public NoisyNAFCPngScene taskScene() {
        NoisyNAFCPngScene scene = new NoisyNAFCPngScene();
        scene.setRenderer(pngConfig.config.experimentGLRenderer());
        scene.setFixation(pngConfig.classicConfig.experimentFixationPoint());
        scene.setMarker(pngConfig.classicConfig.screenMarker());
        scene.setBlankScreen(new BlankScreen());
        scene.setScreenHeight(pngConfig.classicConfig.xperMonkeyScreenHeight());
        scene.setScreenWidth(pngConfig.classicConfig.xperMonkeyScreenWidth());
        scene.setDistance(pngConfig.classicConfig.xperMonkeyScreenDistance());
        scene.setBackgroundColor(pngConfig.classicConfig.xperBackgroundColor());
        scene.setFrameRate(pngConfig.mStickPngConfig.xperNoiseRate());
        return scene;
    }

    @Bean
    public ProceduralExperimentBlockGen blockGen() {
        ProceduralExperimentBlockGen blockGen = new ProceduralExperimentBlockGen();
        //Dependencies of superclasses
        blockGen.setDbUtil(pngConfig.config.allenDbUtil());
        blockGen.setGlobalTimeUtil(pngConfig.acqConfig.timeClient());
        blockGen.setGeneratorPngPath(pngConfig.mStickPngConfig.generatorPngPath);
        blockGen.setExperimentPngPath(pngConfig.mStickPngConfig.experimentPngPath);
        blockGen.setGeneratorSpecPath(pngConfig.mStickPngConfig.generatorSpecPath);
        blockGen.setPngMaker(pngConfig.mStickPngConfig.pngMaker());
        blockGen.setMaxImageDimensionDegrees(pngConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
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
}