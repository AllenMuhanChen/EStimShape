package org.xper.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.intan.IntanRHD;
import org.xper.intan.stimulation.ManualTriggerIntanRHS;
import org.xper.intan.stimulation.Parameter;

import java.util.ArrayList;
import java.util.Collection;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({IntanRHDConfig.class})
public class IntanRHSConfig extends IntanRHDConfig {
    @Autowired
    IntanRHDConfig rhdConfig;

    @ExternalValue("intan.estim.enabled")
    public boolean intanEStimEnabled;

    @Bean
    public ManualTriggerIntanRHS intan(){
        ManualTriggerIntanRHS intanRHS = new ManualTriggerIntanRHS();
        intanRHS.setIntanClient(rhdConfig.intanClient());
        intanRHS.setDefaultSavePath(rhdConfig.intanDefaultSavePath);
        intanRHS.setDefaultBaseFileName(rhdConfig.intanDefaultBaseFilename);
        intanRHS.setDefaultParameters(defaultRHSParameters());
        return intanRHS;
    }

    @Bean
    public Collection<Parameter<Object>> defaultRHSParameters() {
        Collection<Parameter<Object>> defaultParameters = new ArrayList<Parameter<Object>>();
        return defaultParameters;
    }
}