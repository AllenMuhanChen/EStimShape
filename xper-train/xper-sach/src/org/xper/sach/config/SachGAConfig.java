package org.xper.sach.config;

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
import org.xper.drawing.object.BlankScreen;
import org.xper.sach.SachTrialExperiment;
import org.xper.sach.expt.SachExptScene;
import org.xper.sach.expt.SachExptSpecGenerator;
import org.xper.sach.expt.generate.SachRandomGeneration;
import org.xper.sach.vo.SachExperimentState;


@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(SachConfig.class)
public class SachGAConfig {
	@Autowired ClassicConfig classicConfig;
	@Autowired SachConfig sachConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	
//	@Bean
//	public Experiment experiment() {	// use standard experiment for GA *** this isn't working
//		SlideTrialExperiment xper = new SlideTrialExperiment();
//		xper.setStateObject(experimentState());
//		return xper;
//	}
	
	@Bean
	public SachTrialExperiment experiment() {
		SachTrialExperiment xper = new SachTrialExperiment();
		xper.setStateObject(experimentState());
		xper.setEyeMonitor(classicConfig.eyeMonitor());
		xper.setFirstSlideISI(sachConfig.xperFirstInterSlideInterval());		// these are no longer used -- see SachTrialExperiment
		xper.setFirstSlideLength(sachConfig.xperFirstSlideLength());			// these are no longer used -- see SachTrialExperiment
		xper.setBlankTargetScreenDisplayTime(sachConfig.xperBlankTargetScreenDisplayTime());
		xper.setEarlyTargetFixationAllowableTime(0);	// do not allow eyemovements during last stimulus for GA
		return xper;
	}
	
	@Bean
	public SachExptScene taskScene() {
		SachExptScene scene = new SachExptScene();
		scene.setRenderer(sachConfig.experimentGLRenderer());
		scene.setDbUtil(sachConfig.sachDbUtil());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setDrawResponseSpot(false);
		scene.setStimForegroundColor(classicConfig.xperStimColorForeground());
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
//		gen.setTaskCount(5);												// *** change number of trials generated here
		gen.setRenderer(sachConfig.experimentGLRenderer());					// add same renderer for stimulus generation part (so I can reference shared parameters)
		gen.setGenerator(generator());
		gen.setStimForegroundColor(classicConfig.xperStimColorForeground());
		gen.setStimBackgroundColor(classicConfig.xperStimColorBackground());
		gen.setNumStimPerTrial(classicConfig.xperSlidePerTrial());
		return gen;
	}

	// -shs: set slide length and ISI here (not via db):
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
		state.setSlideLength(classicConfig.xperSlideLength());						// GA slide length -- 300
		state.setInterSlideInterval(classicConfig.xperInterSlideInterval());				// GA slide ISI    -- 200
		state.setDoEmptyTask(classicConfig.xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(classicConfig.xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
		state.setRepeatTrialIfEyeBreak(true);
		state.setAnimation(sachConfig.containsAnimation());
		state.setMinJuice(classicConfig.xperJuiceRewardLength());
		state.setTimeoutBaseDelay(sachConfig.timeoutBaseDelay());
		
		return state;
	}
	
}
