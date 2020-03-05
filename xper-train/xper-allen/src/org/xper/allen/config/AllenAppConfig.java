package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.GaussScene;
import org.xper.allen.app.specGenerators.trainingBlockGen;
import org.xper.allen.experiment.GaussianSpecGenerator;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import(AllenConfig.class)
public class AllenAppConfig {
	@Autowired AllenConfig allenConfig;
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
		return scene;
	}

	@Bean GaussianSpecGenerator generator() {
		GaussianSpecGenerator gen = new GaussianSpecGenerator();
		return gen;
	}
	/*
	@Bean EStimObjDataGenerator egenerator() {
		EStimObjDataGenerator egen = new EStimObjDataGenerator();
		return egen;
	}
	*/
	/*
	@Bean
	public RandGenerationAllen randomGen() {
		RandGenerationAllen gen = new RandGenerationAllen();
		gen.setDbUtil(allenConfig.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setTaskCount(100);
		gen.setGenerator(generator());
		return gen;
	}
	*/

	@Bean
	public trainingBlockGen trainingGen() {
		trainingBlockGen blockgen = new trainingBlockGen();
		blockgen.setDbUtil(allenConfig.allenDbUtil());
		blockgen.setGlobalTimeUtil(acqConfig.timeClient());
		blockgen.setXmlUtil(allenConfig.allenXMLUtil());
		return blockgen;
	}
}