package org.xper.allen.app.estimshape;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.estimshape.EStimExperimentTrialGenerator;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.app.procedural.EStimExperimentSetGenerator;
import org.xper.allen.app.procedural.ProceduralAppConfig;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ProceduralAppConfig.class)
public class EStimExperimentAppConfig {
    @Autowired
    public ProceduralAppConfig proceduralAppConfig;

    @Autowired
    public NAFCMStickPngAppConfig pngConfig;

    @Autowired
    ClassicConfig classicConfig;

    @Autowired
    BaseConfig baseConfig;

    @ExternalValue("generator.set_path")
    String generatorSetPath;

    @Bean
    public EStimExperimentTrialGenerator generator(){
        EStimExperimentTrialGenerator generator = new EStimExperimentTrialGenerator();
        generator.setDbUtil(pngConfig.config.allenDbUtil());
        generator.setGlobalTimeUtil(pngConfig.acqConfig.timeClient());
        generator.setGeneratorPngPath(pngConfig.mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(pngConfig.mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(pngConfig.mStickPngConfig.generatorSpecPath);
        generator.setPngMaker(pngConfig.mStickPngConfig.pngMaker());
        generator.setImageDimensionDegrees(pngConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
        //Dependencies of ProceduuralExperimentgenerator
        generator.setGeneratorNoiseMapPath(proceduralAppConfig.generatorNoiseMapPath);
        generator.setExperimentNoiseMapPath(proceduralAppConfig.experimentNoiseMapPath);
        generator.setNafcTrialDbUtil(proceduralAppConfig.nafcTrialDbUtil());
        generator.setGaSpecPath(proceduralAppConfig.gaSpecPath);
        generator.setRfSource(rfSource());
        generator.setGeneratorSetPath(generatorSetPath);
        return generator;
    }

    @Bean
    public EStimExperimentSetGenerator setGenerator(){
        EStimExperimentSetGenerator setGenerator = new EStimExperimentSetGenerator();
        setGenerator.setGenerator(generator());
        setGenerator.setGeneratorSetPath(generatorSetPath);
        return setGenerator;
    }

    @Bean
    public ReceptiveFieldSource rfSource(){
        ReceptiveFieldSource rfSource = new ReceptiveFieldSource();
        rfSource.setDataSource(baseConfig.dataSource());
        rfSource.setRenderer(classicConfig.experimentGLRenderer());
        return rfSource;
    }
}