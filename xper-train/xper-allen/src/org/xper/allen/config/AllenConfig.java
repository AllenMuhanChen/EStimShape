package org.xper.allen.config;


import java.beans.PropertyVetoException;
import java.util.LinkedList;
import java.util.List;

import javax.sql.DataSource;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.experiment.saccade.AllenDatabaseTaskDataSource;
import org.xper.allen.experiment.saccade.SaccadeExperimentState;
import org.xper.allen.experiment.saccade.SaccadeMarkEveryStepTrialDrawingController;
import org.xper.allen.experiment.saccade.SaccadeTrialExperiment;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.BlankTaskScene;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.exception.DbException;
import org.xper.experiment.ExperimentRunner;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.eye.RobustEyeTargetSelector;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;

import com.mchange.v2.c3p0.ComboPooledDataSource;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class AllenConfig {
	@Autowired BaseConfig baseConfig;
	@Autowired ClassicConfig classicConfig;	
	@Autowired AcqConfig acqConfig;
	
	
	@ExternalValue("jdbc.driver")
	public String jdbcDriver;

	@ExternalValue("jdbc.url")
	public String jdbcUrl;

	@ExternalValue("jdbc.username")
	public String jdbcUserName;

	@ExternalValue("jdbc.password")
	public String jdbcPassword;
	
	
	@ExternalValue("experiment.monkey_window_fullscreen")
	public boolean monkeyWindowFullScreen;
	
	@ExternalValue("experiment.mark_every_step")
	public boolean markEveryStep;
	
	@Bean
	public TaskScene taskScene() {
		BlankTaskScene scene = new BlankTaskScene();
		scene.setRenderer(classicConfig.experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		return scene;
	}

	@Bean
	public AllenDbUtil allenDbUtil() {
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(dataSource());
		return dbUtil;
	}
	
	@Bean
	public AllenXMLUtil allenXMLUtil() {
		AllenXMLUtil xmlUtil = new AllenXMLUtil();
		return xmlUtil;
	}
	@Bean
	public ExperimentConsole experimentConsole () {
		ExperimentConsole console = new ExperimentConsole();
		
		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(classicConfig.consoleRenderer());
		console.setMonkeyScreenDimension(consoleResolution());
		console.setModel(classicConfig.experimentConsoleModel());
		console.setCanvasScaleFactor(3);
		
		ExperimentMessageReceiver receiver = classicConfig.messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	/**Changes resolution of console to be monkeyWindowWidth/2 , monkeyWindowHeight. This is to subvert the two XScreen setup aspect ratio being different from console aspect ratio.  
	 * @author allenchen
	 */
	@Bean
	public Coordinates2D consoleResolution(){
		Coordinates2D monkeyScreenDimension = classicConfig.monkeyWindow().getScreenDimension();
		return new Coordinates2D(monkeyScreenDimension.getX()*2,monkeyScreenDimension.getY());
	}
	
	@Bean
	public DataSource dataSource() {
		ComboPooledDataSource source = new ComboPooledDataSource();
		try {
			source.setDriverClass(jdbcDriver);
		} catch (PropertyVetoException e) {
			throw new DbException(e);
		}
		source.setJdbcUrl(jdbcUrl);
		source.setUser(jdbcUserName);
		source.setPassword(jdbcPassword);
		return source;
	}
	
	@Bean
	public AllenDatabaseTaskDataSource databaseTaskDataSource () {
		AllenDatabaseTaskDataSource source = new AllenDatabaseTaskDataSource();
		source.setDbUtil(allenDbUtil());
		source.setQueryInterval(1000);
		source.setUngetBehavior(UngetPolicy.HEAD);
		return source;
	}
	
	@Bean
	public ExperimentRunner experimentRunner () {
		ExperimentRunner runner = new ExperimentRunner();
		runner.setHost(classicConfig.experimentHost);
		runner.setExperiment(experiment());
		return runner;
	}
	
	@Bean
	public SaccadeTrialExperiment experiment() {
		SaccadeTrialExperiment xper = new SaccadeTrialExperiment();
		xper.setEyeMonitor(classicConfig.eyeMonitor());
		xper.setStateObject(experimentState());
		xper.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		xper.setDbUtil(allenDbUtil());
		return xper;
	}

	@Bean
	public SaccadeExperimentState experimentState() {
		SaccadeExperimentState state = new SaccadeExperimentState();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(classicConfig.trialEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(classicConfig.experimentEventListeners());
		state.setTaskDataSource(databaseTaskDataSource());
		state.setTaskDoneCache(classicConfig.taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setDrawingController(drawingController());
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
		state.setTargetSelector(eyeTargetSelector());
		state.setTimeAllowedForInitialTargetSelection(xperTimeAllowedForInitialTargetSelection());  
		state.setRequiredTargetSelectionHoldTime(xperRequiredTargetSelectionHoldTime());
		state.setTargetSelectionStartDelay(xperTargetSelectionEyeMonitorStartDelay());
		state.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		return state;
	}

	private TrialDrawingController drawingController() {
		MarkStimTrialDrawingController controller;
		if (markEveryStep) {
			controller = new SaccadeMarkEveryStepTrialDrawingController();
		} else {
			System.out.println("No option to turn markEveryStep off. Defaulted to markEveryStep on. Change this in AllenConfig");
			controller = new SaccadeMarkEveryStepTrialDrawingController();
		}
		controller.setWindow(classicConfig.monkeyWindow());
		controller.setTaskScene(classicConfig.taskScene());
		controller.setFixationOnWithStimuli(classicConfig.xperFixationOnWithStimuli());
		return controller;
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
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<EyeSamplerEventListener> eyeSamplerEventListeners () {
		List<EyeSamplerEventListener> sampleListeners = new LinkedList<EyeSamplerEventListener>();
		sampleListeners.add(eyeTargetSelector());
		sampleListeners.add(classicConfig.eyeMonitor());
		return sampleListeners;
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
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperBlankTargetScreenDisplayTime() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_blank_target_screen_display_time", 0));
	}


	
}
	