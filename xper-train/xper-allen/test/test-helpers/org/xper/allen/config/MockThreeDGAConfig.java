package org.xper.allen.config;

import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.MockClassicSlideRunner;
import org.xper.allen.ga.MockSlideTrialRunner;
import org.xper.classic.SlideTrialRunner;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({ThreeDGAConfig.class})
public class MockThreeDGAConfig {

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

}
