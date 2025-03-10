package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.allen.saccade.GaussScene;
import org.xper.allen.saccade.blockgen.SimpleEStimBlockGen;
import org.xper.allen.saccade.blockgen.TrainingBlockGen;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import(SimpleEStimConfig.class)
public class SimpleEStimAppConfig {
	@Autowired SimpleEStimConfig simpleEStimConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		
		System.out.println("23108 screen width = " + classicConfig.xperMonkeyScreenWidth());
		
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		renderer.setInverted(classicConfig.xperMonkeyScreenInverted());
		return renderer;
	}
	
	@Bean
	public TaskScene taskScene() {
		GaussScene scene = new GaussScene();
		scene.setRenderer(experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		return scene;
	}
/*
	@Bean GaussianSpecGenerator generator() {
		GaussianSpecGenerator gen = new GaussianSpecGenerator();
		return gen;
	}
*/
	@Bean
	public TrainingBlockGen trainingGen() {
		TrainingBlockGen blockgen = new TrainingBlockGen();
		blockgen.setDbUtil(simpleEStimConfig.allenDbUtil());
		System.out.println(((SimpleEStimConfig) simpleEStimConfig).getJdbcUrl());
		blockgen.setGlobalTimeUtil(acqConfig.timeClient());
		blockgen.setXmlUtil(simpleEStimConfig.allenXMLUtil());
		return blockgen;
	}
	
	@Bean
	public SimpleEStimBlockGen simpleEStimGen() {
		SimpleEStimBlockGen blockgen = new SimpleEStimBlockGen();
		blockgen.setDbUtil(simpleEStimConfig.allenDbUtil());
		System.out.println(((SimpleEStimConfig) simpleEStimConfig).getJdbcUrl());
		blockgen.setGlobalTimeUtil(acqConfig.timeClient());
		blockgen.setXmlUtil(simpleEStimConfig.allenXMLUtil());
		return blockgen;
	}
}