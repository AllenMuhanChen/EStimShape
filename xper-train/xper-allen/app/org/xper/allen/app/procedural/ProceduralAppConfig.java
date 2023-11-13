package org.xper.allen.app.procedural;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.nafc.blockgen.procedural.ProceduralExperimentBlockGen;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import(NAFCMStickPngAppConfig.class)
public class ProceduralAppConfig {
    @Autowired
    NAFCMStickPngAppConfig appConfig;

    @ExternalValue("generator.noisemap_path")
    public String generatorNoiseMapPath;

    @ExternalValue("experiment.noisemap_path")
    public String experimentNoiseMapPath;

    @Bean
    public ProceduralExperimentBlockGen blockGen() {
        ProceduralExperimentBlockGen blockGen = new ProceduralExperimentBlockGen();
        //Dependencies of superclasses
        blockGen.setDbUtil(appConfig.config.allenDbUtil());
        blockGen.setGlobalTimeUtil(appConfig.acqConfig.timeClient());
        blockGen.setGeneratorPngPath(appConfig.mStickPngConfig.generatorPngPath);
        blockGen.setExperimentPngPath(appConfig.mStickPngConfig.experimentPngPath);
        blockGen.setGeneratorSpecPath(appConfig.mStickPngConfig.generatorSpecPath);
        blockGen.setPngMaker(appConfig.mStickPngConfig.pngMaker());
        blockGen.setMaxImageDimensionDegrees(appConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
        //Dependencies of ProceduuralExperimentBlockGen
        blockGen.setGeneratorNoiseMapPath(generatorNoiseMapPath);
        blockGen.setExperimentNoiseMapPath(experimentNoiseMapPath);
        return blockGen;
    }
}