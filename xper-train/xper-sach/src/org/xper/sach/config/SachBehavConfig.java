package org.xper.sach.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
//import org.xper.app.experiment.test.RandomGeneration;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.object.BlankScreen;
//import org.xper.drawing.renderer.AbstractRenderer;
//import org.xper.drawing.renderer.PerspectiveStereoRenderer;
//import org.xper.drawing.renderer.PerspectiveRenderer;  						// don't need stereo for this exp't
import org.xper.sach.expt.SachExptScene;
import org.xper.sach.expt.SachExptSpecGenerator;
import org.xper.sach.expt.generate.SachRandomGeneration;
import org.xper.sach.vo.SachExperimentState;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(SachConfig.class)
public class SachBehavConfig {
	@Autowired ClassicConfig classicConfig;
	@Autowired SachConfig sachConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	

	
//	// -shs: added a timeout penalty delay when a wrong choice is made, as a secondary (negative) reinforcer
//	@Bean(scope = DefaultScopes.PROTOTYPE)
//	public Integer xperTimeoutPenaltyDelay() {
//		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_timeout_penalty_delay", 0));
//	}
	
	@Bean
	public SachExptScene taskScene() {
		SachExptScene scene = new SachExptScene();
		scene.setRenderer(sachConfig.experimentGLRenderer());
		scene.setDbUtil(sachConfig.sachDbUtil());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setDrawResponseSpot(true);
		return scene;
	}
	
	@Bean
	public SachExptSpecGenerator generator() {
		SachExptSpecGenerator gen = new SachExptSpecGenerator();
		gen.setDbUtil(sachConfig.sachDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setRenderer(sachConfig.experimentGLRenderer());
		return gen;
	}
	
	@Bean
	public SachRandomGeneration randomGen() {
		SachRandomGeneration gen = new SachRandomGeneration();
		gen.setDbUtil(sachConfig.sachDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setTaskCount(10);										// *** change number of trials generated here
		gen.setRenderer(sachConfig.experimentGLRenderer());			// add same renderer for stimulus generation part (so I can reference shared parameters)
		gen.setGenerator(generator());
		return gen;
	}
	
	// -shs: for adding 'xperTimeoutPenaltyDelay()'
	@Bean
	public SachExperimentState experimentState() {
		SachExperimentState state = new SachExperimentState();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(sachConfig.trialEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(classicConfig.experimentEventListeners());
		state.setTaskDataSource(sachConfig.databaseTaskDataSource());
		state.setTaskDoneCache(classicConfig.taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setRequiredTargetSelectionHoldTime(sachConfig.xperRequiredTargetSelectionHoldTime());
		state.setTargetSelectionStartDelay(sachConfig.xperTargetSelectionEyeMonitorStartDelay());
		state.setTimeAllowedForInitialTargetSelection(sachConfig.xperTimeAllowedForInitialTargetSelection());
		state.setTargetSelector(sachConfig.eyeTargetSelector());
		state.setDrawingController(sachConfig.drawingController());
		state.setInterTrialInterval(classicConfig.xperInterTrialInterval());
		state.setTimeBeforeFixationPointOn(classicConfig.xperTimeBeforeFixationPointOn());
		state.setTimeAllowedForInitialEyeIn(classicConfig.xperTimeAllowedForInitialEyeIn());
		state.setRequiredEyeInHoldTime(classicConfig.xperRequiredEyeInHoldTime());
		state.setSlidePerTrial(classicConfig.xperSlidePerTrial());
		state.setSlideLength(classicConfig.xperSlideLength());						// slide length
		state.setInterSlideInterval(classicConfig.xperInterSlideInterval());		// slide ISI
		state.setDoEmptyTask(classicConfig.xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(classicConfig.xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
		state.setTimeoutPenaltyDelay(0);
		
		return state;
	}

}
