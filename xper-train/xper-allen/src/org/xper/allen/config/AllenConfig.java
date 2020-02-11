package org.xper.allen.config;


import java.util.LinkedList;
import java.util.List;

import org.lwjgl.opengl.PixelFormat;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.experiment.saccade.SaccadeExperimentState;
import org.xper.allen.experiment.saccade.SaccadeTrialExperiment;
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.drawing.BlankTaskScene;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.AlternatingScreenMarker;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.FixationPoint;
import org.xper.drawing.object.MonkeyWindow;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.eye.RobustEyeTargetSelector;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.sach.SachExperimentMessageDispatcher;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class AllenConfig {
	@Autowired BaseConfig baseConfig;
	@Autowired ClassicConfig classicConfig;	
	@Autowired AcqConfig acqConfig;
	
	@ExternalValue("experiment.monkey_window_fullscreen")
	public boolean monkeyWindowFullScreen;
	
	@ExternalValue("experiment.mark_every_step")
	public boolean markEveryStep;
	
	@Bean
	public TaskScene taskScene() {
		BlankTaskScene scene = new BlankTaskScene();
		scene.setRenderer(experimentGLRenderer());
		scene.setFixation(experimentFixationPoint());
		scene.setMarker(screenMarker());
		scene.setBlankScreen(new BlankScreen());
		return scene;
	}

	@Bean
	public AllenDbUtil allenDbUtil() {
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(baseConfig.dataSource());
		
		return dbUtil;
	}
	
	@Bean
	public DatabaseTaskDataSource databaseTaskDataSource () {
		DatabaseTaskDataSource source = new DatabaseTaskDataSource();
		source.setDbUtil(allenDbUtil());
		source.setQueryInterval(1000);
		source.setUngetBehavior(UngetPolicy.HEAD);
		return source;
	}
	
	@Bean
	public SaccadeTrialExperiment experiment() {
		SaccadeTrialExperiment xper = new SaccadeTrialExperiment();
		xper.setStateObject(experimentState());
		xper.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		return xper;
	}
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperBlankTargetScreenDisplayTime() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_blank_target_screen_display_time", 0));
	}
	
	@Bean
	public SaccadeExperimentState experimentState() {
		SaccadeExperimentState state = new SaccadeExperimentState();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(trialEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(classicConfig.experimentEventListeners());
		state.setTaskDataSource(databaseTaskDataSource());
		state.setTaskDoneCache(classicConfig.taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setTargetSelector(eyeTargetSelector());
		state.setDrawingController(classicConfig.drawingController());
		state.setInterTrialInterval(classicConfig.xperInterTrialInterval());
		state.setTimeBeforeFixationPointOn(classicConfig.xperTimeBeforeFixationPointOn());
		state.setTimeAllowedForInitialEyeIn(classicConfig.xperTimeAllowedForInitialEyeIn());
		state.setRequiredEyeInHoldTime(classicConfig.xperRequiredEyeInHoldTime());
		state.setSlidePerTrial(classicConfig.xperSlidePerTrial());
		state.setSlideLength(classicConfig.xperSlideLength());
		state.setInterSlideInterval(classicConfig.xperInterSlideInterval());
		state.setDoEmptyTask(classicConfig.xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(classicConfig.xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
		//TargetStuff
		state.setTimeAllowedForInitialTargetSelection(xperTimeAllowedForInitialTargetSelection());  
		state.setRequiredTargetSelectionHoldTime(xperRequiredTargetSelectionHoldTime());
		state.setTargetSelectionStartDelay(xperTargetSelectionEyeMonitorStartDelay());
		state.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		return state;
	}

	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
		trialEventListener.add(classicConfig.eyeMonitorController());
		//trialEventListener.add(trialEventLogger());
		trialEventListener.add(classicConfig.experimentProfiler());
		//trialEventListener.add(messageDispatcher());
		trialEventListener.add(classicConfig.juiceController());
		trialEventListener.add(classicConfig.dataAcqController());
		trialEventListener.add(classicConfig.jvmManager());
		return trialEventListener;
	}
	
	@Bean
	public RobustEyeTargetSelector eyeTargetSelector() {
		RobustEyeTargetSelector selector = new RobustEyeTargetSelector();
		selector.setEyeInstrategy(targetSelectorEyeInStrategy());
		selector.setLocalTimeUtil(baseConfig.localTimeUtil());
		selector.setTargetInTimeThreshold(xperTargetSelectionEyeInTimeThreshold());
		selector.setTargetOutTimeThreshold(xperTargetSelectionEyeOutTimeThreshold());
		return selector;
	}
	
	@Bean
	public EyeInStrategy targetSelectorEyeInStrategy() {
		AnyEyeInStategy strategy = new AnyEyeInStategy();
		List<String> devices = new LinkedList<String>();
		devices.add(classicConfig.xperLeftIscanId());
		devices.add(classicConfig.xperRightIscanId());
		strategy.setEyeDevices(devices);
		return strategy;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeInTimeThreshold() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_in_time_threshold", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTimeAllowedForInitialTargetSelection() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_time_allowed_for_initial_target_selection", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperRequiredTargetSelectionHoldTime() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_required_target_selection_hold_time", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeOutTimeThreshold() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_out_time_threshold", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeMonitorStartDelay() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_monitor_start_delay", 0));
	}
}
	