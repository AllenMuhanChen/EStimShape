package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.springframework.core.annotation.Order;
import org.xper.allen.ga.*;
import org.xper.allen.ga.regimescore.LineageScoreSource;
import org.xper.allen.ga.regimescore.MaxValueLineageScore;
import org.xper.allen.newga.blockgen.NewGABlockGenerator;
import org.xper.classic.SlideTrialRunner;
import org.xper.config.BaseConfig;

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
    public MockClassicSlideRunner slideRunner() {
        return new MockClassicSlideRunner();
    }


    @Bean
    public MockSpikeRateSource spikeRateSource(){
        MockSpikeRateSource spikeRateSource = new MockSpikeRateSource();
        spikeRateSource.setDbUtil(config.dbUtil());
        spikeRateSource.setGaName(NewGABlockGenerator.gaBaseName);
        return spikeRateSource;
    }
}