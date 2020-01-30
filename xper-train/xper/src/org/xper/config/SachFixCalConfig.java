package org.xper.config;

import java.util.LinkedList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.classic.SlideTrialExperiment;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.FixCalConfig;
import org.xper.drawing.object.BlankScreen;
import org.xper.experiment.Experiment;
import org.xper.eye.mapping.LinearMappingAlgorithm;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.win.RampEyeWindowAlgorithm;
import org.xper.fixcal.FixCalEventListener;
import org.xper.fixcal.FixationCalibration;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(FixCalConfig.class)
public class SachFixCalConfig {
	@Autowired FixCalConfig fixCalConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	
	
	@Bean
	public FixationCalibration taskScene() {
		FixationCalibration scene = new FixationCalibration();
		scene.setFixation(fixCalConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setRenderer(fixCalConfig.experimentGLRenderer());
		scene.setCalibrationDegree(5.0);
		scene.setFixationPoint(fixCalConfig.experimentFixationPoint());
		scene.setEyeMonitor(classicConfig.eyeMonitor());
		scene.setDeviceDbVariableMap(classicConfig.xperEyeDeviceParameterIdDbVariableMap());
		scene.setEyeZeroDbVariableMap(classicConfig.xperEyeZeroIdDbVariableMap());
		List<FixCalEventListener> fixCalEventListeners = new LinkedList<FixCalEventListener>();
		fixCalEventListeners.add(fixCalConfig.messageDispatcher());
		scene.setFixCalEventListeners(fixCalEventListeners);
		scene.setDbUtil(baseConfig.dbUtil());
		return scene;
	}

	
	// trying to override the one in ClassicConfig:
	
	@Bean
	public Experiment experiment () {
		SlideTrialExperiment xper = new SlideTrialExperiment();
		xper.setStateObject(experimentState());
		return xper;
	}
	
	@Bean
	public SlideTrialExperimentState experimentState () {
		SlideTrialExperimentState state = new SlideTrialExperimentState ();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(fixCalConfig.trialEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(fixCalConfig.experimentEventListeners());
		state.setTaskDataSource(fixCalConfig.taskDataSource());
		state.setTaskDoneCache(fixCalConfig.taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setDrawingController(classicConfig.drawingController());
		state.setInterTrialInterval(classicConfig.xperInterTrialInterval());
		state.setTimeBeforeFixationPointOn(classicConfig.xperTimeBeforeFixationPointOn());
		state.setTimeAllowedForInitialEyeIn(classicConfig.xperTimeAllowedForInitialEyeIn());
		state.setRequiredEyeInHoldTime(classicConfig.xperRequiredEyeInHoldTime());
		state.setSlidePerTrial(1);				// these are to set the total fixation time
		state.setSlideLength(500);				// msec
		state.setInterSlideInterval(500);		// msec
		state.setDoEmptyTask(classicConfig.xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(classicConfig.xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
		return state;
	}
	
	@Bean
	public RampEyeWindowAlgorithm eyeWindowAlgorithm() {
		RampEyeWindowAlgorithm algo = new RampEyeWindowAlgorithm();
		algo.setBaseWindowSize(10);
		algo.setInitialWindowSize(10);
		algo.setRampLength(20);
		algo.init();
		
		return algo;
	}
	
	// trying to override initial mapping algorithm values:
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public MappingAlgorithm rightIscanMappingAlgorithm() {
		LinearMappingAlgorithm algorithm = new LinearMappingAlgorithm();
		algorithm.setSxh(1);
		algorithm.setSxv(0);  
		algorithm.setSyh(0);
		algorithm.setSyv(1);
		return algorithm;
	}
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public LinearMappingAlgorithm leftIscanMappingAlgorithm() {
		LinearMappingAlgorithm a = new LinearMappingAlgorithm();
		a.setSxh(1);
		a.setSxv(0);
		a.setSyh(0);
		a.setSyv(1);
		return a;
	}
	
}
