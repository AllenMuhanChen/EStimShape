package org.xper.sach.config;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;

import org.lwjgl.opengl.PixelFormat;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.MonkeyWindow;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.eye.RobustEyeTargetSelector;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.juice.mock.NullDynamicJuice;
import org.xper.sach.DefaultSachTrialDrawingController;
import org.xper.sach.SachExperimentConsoleRenderer;
import org.xper.sach.SachExperimentJuiceController;
import org.xper.sach.SachExperimentMessageDispatcher;
import org.xper.sach.SachExperimentMessageHandler;
import org.xper.sach.SachTrialEventLogger;
import org.xper.sach.SachTrialExperiment;
import org.xper.sach.analysis.BehavAnalysisFrame;
import org.xper.sach.analysis.GAAnalysisFrame;
import org.xper.sach.expt.SachDatabaseTaskDataSource;
import org.xper.sach.renderer.SachPerspectiveStereoRenderer;
import org.xper.sach.util.SachDbUtil;
import org.xper.sach.vo.SachExperimentState;

/**
 * Project for Sach
 * 
 * 1 to 10 objects.
 * 
 * select target at then end of the trial
 *  
 * @author john
 *
 */

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class SachConfig {
	@Autowired BaseConfig baseConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	
	
	@Bean
	public SachDbUtil sachDbUtil() {
		SachDbUtil util = new SachDbUtil();
		util.setDataSource(baseConfig.dataSource());
		return util;
	}
	
	@Bean
	public ExperimentConsole experimentConsole() {
		ExperimentConsole console = new ExperimentConsole();
		
		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(consoleRenderer());
		console.setMonkeyScreenDimension(monkeyWindow().getScreenDimension());
		console.setModel(classicConfig.experimentConsoleModel());
//		console.setCanvasScaleFactor(2.5);
		
		ExperimentMessageReceiver receiver = classicConfig.messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	
	@Bean
	public AbstractRenderer consoleGLRenderer() {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth()/2);	// TODO: I changed this! -shs (divided by 2, was squashed)
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
	}
	
	@Bean
	public MonkeyWindow monkeyWindow() {
		MonkeyWindow win = new MonkeyWindow();
		win.setFullscreen(classicConfig.monkeyWindowFullScreen);
		// enable alpha, depth and stencil buffer
		win.setPixelFormat(new PixelFormat(0, 8, 1, 4));	// shs -- added "4" here to enable multisample
//		win.setPixelFormat(new PixelFormat(0, 8, 1));
		return win;
	}
	
	@Bean
	public SachTrialExperiment experiment() {
		SachTrialExperiment xper = new SachTrialExperiment();
		xper.setStateObject(experimentState());
		xper.setEyeMonitor(classicConfig.eyeMonitor());
		xper.setFirstSlideISI(xperFirstInterSlideInterval());		// these are no longer used -- see SachTrialExperiment
		xper.setFirstSlideLength(xperFirstSlideLength());			// these are no longer used -- see SachTrialExperiment
		xper.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		xper.setEarlyTargetFixationAllowableTime(xperEarlyTargetFixationAllowableTime());
		return xper;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperFirstSlideLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_first_slide_length", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperFirstInterSlideInterval() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_first_inter_slide_interval", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperBlankTargetScreenDisplayTime() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_blank_target_screen_display_time", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperEarlyTargetFixationAllowableTime() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_early_target_fixation_allowable_time", 0));
	}

	@Bean
	public SachExperimentState experimentState() {
		SachExperimentState state = new SachExperimentState();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(trialEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(classicConfig.experimentEventListeners());
		state.setTaskDataSource(databaseTaskDataSource());
		state.setTaskDoneCache(classicConfig.taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setRequiredTargetSelectionHoldTime(xperRequiredTargetSelectionHoldTime());
		state.setTargetSelectionStartDelay(xperTargetSelectionEyeMonitorStartDelay());
		state.setTimeAllowedForInitialTargetSelection(xperTimeAllowedForInitialTargetSelection());
		state.setTargetSelector(eyeTargetSelector());
		state.setDrawingController(drawingController());
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
		state.setRepeatTrialIfEyeBreak(false); // TODO: set to true if I allow eye movements during last stim (less false breaks!)

		return state;
	}
	
	@Bean
	public SachDatabaseTaskDataSource databaseTaskDataSource () {
		SachDatabaseTaskDataSource source = new SachDatabaseTaskDataSource();
		source.setDbUtil(sachDbUtil());
		source.setQueryInterval(1000);
//		source.setUngetBehavior(UngetPolicy.TAIL);
		source.setUngetBehavior(UngetPolicy.HEAD);
		return source;
	}
	
	@Bean
	public SachExperimentMessageHandler messageHandler() {
		SachExperimentMessageHandler messageHandler = new SachExperimentMessageHandler();
		HashMap<String, EyeDeviceReading> eyeDeviceReading = new HashMap<String, EyeDeviceReading>();
		eyeDeviceReading.put(classicConfig.xperLeftIscanId(), classicConfig.zeroEyeDeviceReading());
		eyeDeviceReading.put(classicConfig.xperRightIscanId(), classicConfig.zeroEyeDeviceReading());
		messageHandler.setEyeDeviceReading(eyeDeviceReading);
		messageHandler.setEyeWindow(new EyeWindow(classicConfig.xperEyeWindowCenter(), classicConfig.xperEyeWindowAlgorithmInitialWindowSize()));
		HashMap<String, Coordinates2D> eyeZero = new HashMap<String, Coordinates2D>();
		eyeZero.put(classicConfig.xperLeftIscanId(), classicConfig.xperLeftIscanEyeZero());
		eyeZero.put(classicConfig.xperRightIscanId(), classicConfig.xperRightIscanEyeZero());
		messageHandler.setEyeZero(eyeZero);
		return messageHandler;
	}
	
	@Bean
	public SachExperimentConsoleRenderer consoleRenderer () {
		SachExperimentConsoleRenderer renderer = new SachExperimentConsoleRenderer();
		renderer.setMessageHandler(messageHandler());
		renderer.setFixation(classicConfig.consoleFixationPoint());
		renderer.setRenderer(consoleGLRenderer());
		renderer.setBlankScreen(new BlankScreen());
		renderer.setCircle(new Circle());
		renderer.setSquare(new Square());
		return renderer;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
		trialEventListener.add(classicConfig.eyeMonitorController());
		trialEventListener.add(trialEventLogger());
		trialEventListener.add(classicConfig.experimentProfiler());
		trialEventListener.add(messageDispatcher());
		trialEventListener.add(classicConfig.juiceController());
		trialEventListener.add(classicConfig.trialSyncController());
		trialEventListener.add(classicConfig.dataAcqController());
		trialEventListener.add(classicConfig.jvmManager());
		return trialEventListener;
	}
	
	@Bean
	public SachTrialEventLogger trialEventLogger() {
		SachTrialEventLogger logger = new SachTrialEventLogger();
		return logger;
	}
	
	@Bean
	public TrialDrawingController drawingController() {
		DefaultSachTrialDrawingController controller;
		controller = new DefaultSachTrialDrawingController();
		controller.setWindow(monkeyWindow());
		controller.setTaskScene(classicConfig.taskScene());
		controller.setFixationOnWithStimuli(classicConfig.xperFixationOnWithStimuli());
		return controller;
	}
	
	@Bean
	public SachExperimentMessageDispatcher messageDispatcher() {
		SachExperimentMessageDispatcher dispatcher = new SachExperimentMessageDispatcher();
		dispatcher.setHost(classicConfig.experimentHost);
		dispatcher.setDbUtil(sachDbUtil());
		return dispatcher;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<EyeSamplerEventListener> eyeSamplerEventListeners () {
		List<EyeSamplerEventListener> sampleListeners = new LinkedList<EyeSamplerEventListener>();
		sampleListeners.add(eyeTargetSelector());
		sampleListeners.add(classicConfig.eyeMonitor());
		return sampleListeners;
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
	public Long xperTimeAllowedForInitialTargetSelection() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_time_allowed_for_initial_target_selection", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperRequiredTargetSelectionHoldTime() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_required_target_selection_hold_time", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeInTimeThreshold() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_in_time_threshold", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeOutTimeThreshold() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_out_time_threshold", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeMonitorStartDelay() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_monitor_start_delay", 0));
	}
	
	/*@Bean
	public DigitalPortJuice xperDynamicJuice() {
		DigitalPortJuice juice = new DigitalPortJuice();
		juice.setTriggerDelay(acqConfig.digitalPortJuiceTriggerDelay);
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NI)) {
			juice.setDevice(classicConfig.niDigitalPortJuiceDevice());
		} else if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_COMEDI)) {
			juice.setDevice(classicConfig.comediDigitalPortJuiceDevice());
		} else {
			throw new ExperimentSetupException("Acq driver " + acqConfig.acqDriverName + " not supported.");
		}
		return juice;
	}*/
	
	@Bean
	public TrialEventListener juiceController() {
		SachExperimentJuiceController controller = new SachExperimentJuiceController();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			controller.setJuice(new NullDynamicJuice());
		} else {
			controller.setJuice(classicConfig.xperDynamicJuice());
		}
		return controller;
	}
	
	// *** added by SHS ***  
	
	/*	@Bean
	public SachPerspectiveRenderer experimentGLRenderer () {
		//PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
		//PerspectiveRenderer renderer = new PerspectiveRenderer();				// not using stereo
		SachPerspectiveRenderer renderer = new SachPerspectiveRenderer();		// using my version w background color setting
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		//renderer.setInverted(classicConfig.xperMonkeyScreenInverted());  		// only used for stereo rendering
		renderer.setRgbColor(new RGBColor(0.5f,0.5f,0.5f));						// set background color to gray		
		return renderer;
	}*/
	
	@Bean
	public SachPerspectiveStereoRenderer experimentGLRenderer () {
//		PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
		//PerspectiveRenderer renderer = new PerspectiveRenderer();				// not using stereo
		SachPerspectiveStereoRenderer renderer = new SachPerspectiveStereoRenderer();		// using my version w background color setting
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		renderer.setInverted(classicConfig.xperMonkeyScreenInverted());  		// only used for stereo rendering
		renderer.setRgbColor(classicConfig.xperStimColorBackground());						// set background color to gray
		renderer.setDoStereo(sachDbUtil().readReadyGenerationInfo().getUseStereoRenderer());
		return renderer;
	}
	
	@Bean
	public BehavAnalysisFrame setBehavAnal() {								// used for analysis window
		BehavAnalysisFrame anal = new BehavAnalysisFrame();
		anal.setDbUtil(sachDbUtil());
		//anal.setGlobalTimeUtil(acqConfig.timeClient());
		return anal;
	}
	
	@Bean
	public GAAnalysisFrame setGAAnal() {								// used for analysis window
		GAAnalysisFrame anal = new GAAnalysisFrame();
		anal.setDbUtil(sachDbUtil());
		//anal.setGlobalTimeUtil(acqConfig.timeClient());
		return anal;
	}
	
	public boolean containsAnimation() {
		return sachDbUtil().containsAnimation();
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long timeoutBaseDelay() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_timeout_base_delay", 0));
	}
	
}
