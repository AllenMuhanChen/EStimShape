package org.xper.allen.monitorlinearization;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.IntanRHDConfig;
import org.xper.drawing.object.BlankScreen;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class MonLinConfig {
    @Autowired ClassicConfig classicConfig;
    @Autowired
    BaseConfig baseConfig;
    @Bean
    public MonLinScene taskScene(){
        MonLinScene scene = new MonLinScene();
        scene.setRenderer(classicConfig.experimentGLRenderer());
        scene.setFixation(classicConfig.experimentFixationPoint());
        scene.setMarker(classicConfig.screenMarker());
        scene.setBlankScreen(new BlankScreen());
        scene.setBackgroundColor(classicConfig.xperBackgroundColor());
        return scene;
    }

    @Bean
    public MonLinTrialGenerator trialGenerator(){
        MonLinTrialGenerator gen = new MonLinTrialGenerator();
        gen.setDbUtil(baseConfig.dbUtil());
        gen.setGlobalTimeUtil(baseConfig.localTimeUtil());
        return gen;

    }


}