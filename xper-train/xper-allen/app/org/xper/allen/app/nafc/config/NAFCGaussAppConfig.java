package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.nafc.NAFCTrialExperiment;
import org.xper.allen.nafc.NAFCGaussScene;
import org.xper.allen.nafc.NAFCTaskScene;
import org.xper.allen.nafc.blockgen.TestBlockGen;
import org.xper.allen.saccade.GaussScene;
import org.xper.allen.saccade.blockgen.SimpleEStimBlockGen;
import org.xper.allen.saccade.blockgen.TrainingBlockGen;
import org.xper.app.experiment.test.RandomGeneration;
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

@Import(NAFCConfig.class)
/**
 * methods written here will OVERRIDE methods with identical name in config. 
 * @author r2_allen
 *
 */
public class NAFCAppConfig {
	@Autowired NAFCConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	@Bean
	public NAFCTrialExperiment experiment() {
		NAFCTrialExperiment xper = new NAFCTrialExperiment();
		xper.setEyeMonitor(classicConfig.eyeMonitor());
		xper.setStateObject(config.experimentState());
		xper.setBlankTargetScreenDisplayTime(config.xperBlankTargetScreenDisplayTime());
		xper.setDbUtil(config.allenDbUtil());
		return xper;
	}
	
	@Bean
	public NAFCGaussScene taskScene() {
		NAFCGaussScene scene = new NAFCGaussScene();
		scene.setRenderer(config.experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		return scene;
	}
	
	@Bean
	public TestBlockGen generator() {
		TestBlockGen gen = new TestBlockGen();
		gen.setDbUtil(config.allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setXmlUtil(config.allenXMLUtil());
		return gen;
	}
	
/*
	@Bean GaussianSpecGenerator generator() {
		GaussianSpecGenerator gen = new GaussianSpecGenerator();
		return gen;
	}
*/
	/*
	@Bean
	public TrainingBlockGen trainingGen() {
		TrainingBlockGen blockgen = new TrainingBlockGen();
		blockgen.setDbUtil(config.allenDbUtil());
		//System.out.println(((ChoiceInRFAppConfig) config).getJdbcUrl());
		blockgen.setGlobalTimeUtil(acqConfig.timeClient());
		blockgen.setXmlUtil(config.allenXMLUtil());
		return blockgen;
	}
	
	@Bean
	public SimpleEStimBlockGen simpleEStimGen() {
		SimpleEStimBlockGen blockgen = new SimpleEStimBlockGen();
		blockgen.setDbUtil(config.allenDbUtil());
		//System.out.println(((ChoiceInRFAppConfig) config).getJdbcUrl());
		blockgen.setGlobalTimeUtil(acqConfig.timeClient());
		blockgen.setXmlUtil(config.allenXMLUtil());
		return blockgen;
	}
	*/
}