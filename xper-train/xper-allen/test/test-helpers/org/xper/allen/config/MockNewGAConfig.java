package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.newga.blockgen.SlotGABlockGenerator;
import org.xper.classic.SlideTrialRunner;

@Configuration(defaultLazy = Lazy.TRUE)
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
    public MockNoDrawSlideRunner slideRunner() {
        return new MockNoDrawSlideRunner();
    }


    @Bean
    public MockSpikeRateSource spikeRateSource(){
        MockSpikeRateSource spikeRateSource = new MockSpikeRateSource();
        spikeRateSource.setDbUtil(config.dbUtil());
        spikeRateSource.setGaName(SlotGABlockGenerator.gaBaseName);
        return spikeRateSource;
    }
}