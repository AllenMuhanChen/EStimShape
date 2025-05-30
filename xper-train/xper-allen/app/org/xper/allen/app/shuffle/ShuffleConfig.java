package org.xper.allen.app.shuffle;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.twodvsthreed.TwoDVsThreeDConfig;
import org.xper.allen.config.MStickPngConfig;
import org.xper.allen.shuffle.ShuffleTrialGenerator;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(TwoDVsThreeDConfig.class)
public class ShuffleConfig {
    @Autowired
    TwoDVsThreeDConfig config;
    @Autowired
    ClassicConfig classicConfig;
    @Autowired
    BaseConfig baseConfig;
    @Autowired
    MStickPngConfig pngConfig;
    @Bean
    public ShuffleTrialGenerator generator(){
        ShuffleTrialGenerator generator = new ShuffleTrialGenerator();
        generator.setGaDataSource(config.gaDataSource());
        generator.setGaSpecPath(config.gaSpecPath);
        generator.setRfSource(config.rfSource());
        generator.setDbUtil(baseConfig.dbUtil());
        generator.setExperimentPngPath(pngConfig.experimentPngPath);
        generator.setGeneratorPngPath(pngConfig.generatorPngPath);
        generator.setGeneratorSpecPath(pngConfig.generatorSpecPath);
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setPngMaker(pngConfig.pngMaker());
        generator.setImageDimensionDegrees(pngConfig.xperMaxImageDimensionDegrees());
        return generator;
    }
}