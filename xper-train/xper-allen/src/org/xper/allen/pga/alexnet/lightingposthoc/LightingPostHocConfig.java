package org.xper.allen.pga.alexnet.lightingposthoc;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.pga.alexnet.AlexNetConfig;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import({AlexNetConfig.class})
public class LightingPostHocConfig {
    @Autowired AlexNetConfig gaConfig;

    @Bean
    public LightingPostHocGenerator generator(){
        LightingPostHocGenerator generator = new LightingPostHocGenerator();
        generator.setDbUtil(gaConfig.dbUtil());
        generator.setGeneratorPngPath(gaConfig.generatorPngPath);
        generator.setGeneratorSpecPath(gaConfig.generatorSpecPath);
        generator.setDrawingManager(gaConfig.drawingManager());
        generator.setGlobalTimeUtil(gaConfig.localTimeUtil());
        return generator;
    }


}