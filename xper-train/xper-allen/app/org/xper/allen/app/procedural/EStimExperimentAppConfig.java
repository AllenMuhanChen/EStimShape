package org.xper.allen.app.procedural;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
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
        return generator;
    }

    @Bean
    public ReceptiveFieldSource rfSource(){
        ReceptiveFieldSource rfSource = new ReceptiveFieldSource();
        rfSource.setDataSource(baseConfig.dataSource());
        rfSource.setRenderer(classicConfig.experimentGLRenderer());
        return rfSource;
    }
}