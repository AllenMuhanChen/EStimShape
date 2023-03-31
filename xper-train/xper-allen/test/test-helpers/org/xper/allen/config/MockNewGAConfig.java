package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.ga.*;
import org.xper.classic.SlideTrialRunner;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({NewGAConfig.class})
public class MockNewGAConfig {
    @Autowired
    NewGAConfig config;

    @Bean
    public SlideTrialRunner slideTrialRunner(){
        MockSlideTrialRunner slideTrialRunner = new MockSlideTrialRunner();
        slideTrialRunner.setSlideRunner(slideRunner());
        return slideTrialRunner;
    }

    @Bean
    public MockClassicSlideRunner slideRunner() {
        return new MockClassicSlideRunner();
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public SpikeRateSource spikeRateSource(){
        MockSpikeRateSource spikeRateSource = new MockSpikeRateSource();
        spikeRateSource.setDbUtil(config.dbUtil());
        spikeRateSource.setGaName(config.generator().getGaBaseName());
        return spikeRateSource;
    }


}