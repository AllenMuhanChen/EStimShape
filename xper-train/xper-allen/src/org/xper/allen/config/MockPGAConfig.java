package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.ga.MockNoDrawSlideRunner;
import org.xper.allen.ga.MockSlideTrialRunner;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideTrialRunner;
import org.xper.classic.TrialEventListener;
import org.xper.config.ClassicConfig;
import org.xper.experiment.listener.ExperimentEventListener;

import java.util.LinkedList;
import java.util.List;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({PGAConfig.class})
public class MockPGAConfig {
    @Autowired PGAConfig config;
    @Autowired ClassicConfig classicConfig;
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


    @Bean(scope = DefaultScopes.PROTOTYPE)
    public List<ExperimentEventListener> experimentEventListeners () {
        List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
        listeners.add(classicConfig.messageDispatcher());
        listeners.add(classicConfig.databaseTaskDataSourceController());
        listeners.add(classicConfig.messageDispatcherController());
        listeners.add(classicConfig.intanRecordingController());
        return listeners;
    }

    @Bean (scope = DefaultScopes.PROTOTYPE)
    public List<TrialEventListener> trialEventListeners () {
        List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
        trialEventListener.add(classicConfig.messageDispatcher());
        trialEventListener.add(classicConfig.intanRecordingController());
        return trialEventListener;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public List<SlideEventListener> slideEventListeners () {
        List<SlideEventListener> listeners = new LinkedList<SlideEventListener>();
        listeners.add(classicConfig.messageDispatcher());
        listeners.add(classicConfig.intanRecordingController());
        return listeners;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Boolean xperDoEmptyTask() {
        return false;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Integer xperInterTrialInterval() {
        return 1;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Integer xperDelayAfterTrialComplete() {
        return 0;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Integer xperTimeBeforeFixationPointOn() {
        return 0;
    }


}