package org.xper.allen.app.estimshape;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.app.procedural.EStimShapeExperimentSetGenerator;
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
    public EStimShapeExperimentTrialGenerator generator(){
        EStimShapeExperimentTrialGenerator generator = new EStimShapeExperimentTrialGenerator();
        generator.setDbUtil(pngConfig.config.allenDbUtil());
        generator.setGlobalTimeUtil(pngConfig.acqConfig.timeClient());
        generator.setGeneratorPngPath(pngConfig.mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(pngConfig.mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(pngConfig.mStickPngConfig.generatorSpecPath);
        generator.setPngMaker(pngConfig.mStickPngConfig.pngMaker());
        generator.setImageDimensionDegrees(pngConfig.mStickPngConfig.xperMaxImageDimensionDegrees());
        generator.setNoiseMapper(pngConfig.mStickPngConfig.noiseMapper());
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
    public EStimShapeExperimentSetGenerator setGenerator(){
        EStimShapeExperimentSetGenerator setGenerator = new EStimShapeExperimentSetGenerator();
        setGenerator.setGenerator(generator());
        setGenerator.setGeneratorSetPath(generatorSetPath);
        setGenerator.setNoiseMapper(pngConfig.mStickPngConfig.noiseMapper());
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