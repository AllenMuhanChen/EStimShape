package org.xper.allen.config;


import java.beans.PropertyVetoException;
import java.util.*;

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
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.allen.intan.NAFCTrialIntanStimulationRecordingController;
import org.xper.allen.intan.NAFCTrialTriggerIntanStimulationRecordingController;
import org.xper.allen.nafc.experiment.*;
import org.xper.allen.nafc.eye.NAFCEyeMonitorController;
import org.xper.config.*;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.allen.intan.EStimEventListener;
import org.xper.allen.nafc.NAFCGaussScene;
import org.xper.allen.nafc.NAFCTaskScene;
import org.xper.allen.nafc.console.NAFCExperimentConsole;
import org.xper.allen.nafc.console.NAFCExperimentConsoleModel;
import org.xper.allen.nafc.console.NAFCExperimentConsoleRenderer;
import org.xper.allen.nafc.console.NAFCExperimentMessageReceiver;
import org.xper.allen.nafc.message.ChoiceEventListener;
import org.xper.allen.nafc.message.NAFCExperimentMessageDispatcher;
import org.xper.allen.nafc.message.NAFCExperimentMessageHandler;
import org.xper.allen.nafc.experiment.juice.NAFCJuiceController;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.classic.TrialEventListener;
import org.xper.console.MessageReceiverEventListener;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;
import org.xper.exception.DbException;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.eye.RobustEyeTargetSelector;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.juice.mock.NullDynamicJuice;

import com.mchange.v2.c3p0.ComboPooledDataSource;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import({ClassicConfig.class, RewardButtonConfig.class, IntanRHSConfig.class})
public class NAFCConfig {
	@Autowired RewardButtonConfig rewardButtonConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired
	IntanRHSConfig intanConfig;
	@Autowired
	IntanRHDConfig rhdConfig;

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

	@ExternalValue("screenshot.enabled")
	public boolean screenShotEnabled;

	@ExternalValue("screenshot.directory")
	public String screenShotDirectory;

	public String getJdbcUrl() {
		return jdbcUrl;
	}



	/**
	 * When switching to Perspective Renderer we need to make sure the xper-window-length is precisely
	 * the same width as the actual screen.
	 * @return
	 */
	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
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
	public NAFCExperimentConsole experimentConsole () {
		NAFCExperimentConsole console = new NAFCExperimentConsole();

		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(consoleRenderer());
		console.setMonkeyScreenDimension(classicConfig.monkeyWindow().getScreenDimension());
		console.setModel(experimentConsoleModel());
		console.setCanvasScaleFactor(3);

		NAFCExperimentMessageReceiver receiver = messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);

		return console;
	}

	@Bean
	public NAFCExperimentMessageReceiver messageReceiver () {
		NAFCExperimentMessageReceiver receiver = new NAFCExperimentMessageReceiver();
		receiver.setReceiverHost(classicConfig.consoleHost);
		receiver.setDispatcherHost(classicConfig.experimentHost);
		LinkedList<MessageReceiverEventListener> messageReceiverEventListeners = new LinkedList<MessageReceiverEventListener>();
		// let console to register itself to avoid circular reference
		// messageReceiverEventListeners.add(console);
		receiver.setMessageReceiverEventListeners(messageReceiverEventListeners);
		receiver.setMessageHandler(messageHandler());

		return receiver;
	}

	@Bean
	public NAFCExperimentConsoleModel experimentConsoleModel () {
		NAFCExperimentConsoleModel model = new NAFCExperimentConsoleModel();
		model.setMessageReceiver(messageReceiver());
		model.setLocalTimeUtil(baseConfig.localTimeUtil());

		HashMap<String, MappingAlgorithm> eyeMappingAlgorithm = new HashMap<String, MappingAlgorithm>();
		eyeMappingAlgorithm.put(classicConfig.xperLeftIscanId(), classicConfig.leftIscanMappingAlgorithm());
		eyeMappingAlgorithm.put(classicConfig.xperRightIscanId(), classicConfig.rightIscanMappingAlgorithm());
		model.setEyeMappingAlgorithm(eyeMappingAlgorithm);

		model.setExperimentRunnerClient(rewardButtonConfig.experimentRunnerClient());
		model.setChannelMap(classicConfig.iscanChannelMap());
		model.setMessageHandler(messageHandler());

		if (classicConfig.consoleEyeSimulation || acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			// socket sampling server for eye simulation
			SocketSamplingDeviceServer server = new SocketSamplingDeviceServer();
			server.setHost(classicConfig.consoleHost);
			server.setSamplingDevice(model);
			HashMap<Integer, Double> data = new HashMap<Integer, Double>();
			data.put(classicConfig.xperLeftIscanXChannel(), new Double(0));
			data.put(classicConfig.xperLeftIscanYChannel(), new Double(0));
			data.put(classicConfig.xperRightIscanXChannel(), new Double(0));
			data.put(classicConfig.xperRightIscanYChannel(), new Double(0));
			server.setCurrentChannelData(data);

			model.setSamplingServer(server);
		}


		return model;
	}


	@Bean
	public NAFCExperimentConsoleRenderer consoleRenderer () {
		NAFCExperimentConsoleRenderer renderer = new NAFCExperimentConsoleRenderer();
		/*
		 * There's a messageHandler and saccadeMessageHandler because I don't know how to overwrite @Bean Dependencies.
		 * This could be reduced to just one method by making one messageHandler that's just copy pasting TrialExperimentMessageHandler with SaccadeExperimentMessageHandler methods inside.
		 */
		//renderer.setMessageHandler(classicConfig.messageHandler());
		renderer.setNAFCExperimentMessageHandler(messageHandler());
		renderer.setFixation(classicConfig.consoleFixationPoint());
		renderer.setRenderer(consoleGLRenderer());
		renderer.setBlankScreen(new BlankScreen());
		renderer.setCircle(new Circle());
		renderer.setSquare(new Square());
		return renderer;
	}


	@Bean
	public NAFCExperimentMessageHandler  messageHandler() {
		NAFCExperimentMessageHandler messageHandler = new NAFCExperimentMessageHandler();
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
	public AbstractRenderer consoleGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
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
	public NAFCDatabaseTaskDataSource databaseTaskDataSource() {
		NAFCDatabaseTaskDataSource source = new NAFCDatabaseTaskDataSource();
		source.setDbUtil(allenDbUtil());
		source.setQueryInterval(1000);
		source.setUngetBehavior(xperUngetPolicy());
		source.setUngetTaskThreshold(xperUngetTaskThreshold());
		return source;
	}

	@Bean
	public int xperUngetTaskThreshold() {
		return 5;
	}

	@Bean
	public NAFCTrialExperiment experiment() {
		NAFCTrialExperiment xper = new NAFCTrialExperiment();
		xper.setEyeMonitor(classicConfig.eyeMonitor());
		xper.setStateObject(experimentState());
		xper.setDbUtil(allenDbUtil());
		xper.setTrialRunner(trialRunner());
		return xper;
	}

	@Bean
	public ClassicNAFCTrialRunner trialRunner(){
		ClassicNAFCTrialRunner trialRunner = new ClassicNAFCTrialRunner();
		trialRunner.setRunner(taskRunner());
		trialRunner.setPunisher(punisher());
		return trialRunner;
	}

	@Bean
	public ClassicNAFCTaskRunner taskRunner(){
		ClassicNAFCTaskRunner taskRunner = new ClassicNAFCTaskRunner();
		//Punishment
		taskRunner.setPunisher(punisher());
		taskRunner.setPunishSampleHoldFail(xperPunishSampleHoldFail());

		//Showing Correct Answer
		taskRunner.setShowAnswer(xperShowAnswer());
		taskRunner.setShowAnswerLength(xperShowAnswerLength());

		//Repeating Incorrect Trials
		taskRunner.setRepeatIncorrectTrials(xperRepeatIncorrectTrials());
		taskRunner.setRepeatSampleFailTrials(xperRepeatSampleFailTrials());
		return taskRunner;
	}

	@Bean
	public NAFCPunisher punisher() {
		NAFCPunisher punisher = new NAFCPunisher();
		punisher.setSampleHoldFailPunishmentTime(xperSampleHoldFailPunishmentTime());
		punisher.setStreakToStartPunishment(classicConfig.xperStreakToStartPunishment());
		punisher.setPunishmentDelayTime(classicConfig.xperPunishmentDelayTime());
		punisher.setPunishmentFixationPoint(classicConfig.punishmentFixationPoint());
		punisher.setOriginalFixationPoint(classicConfig.experimentFixationPoint());
		return punisher;
	}

	@Bean
	public int xperSampleHoldFailPunishmentTime() {
		return (int) (2000 + xperRequiredTargetSelectionHoldTime() + xperShowAnswerLength());
	}

	@Bean
	public boolean xperPunishSampleHoldFail() {
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_punish_sample_hold_fail", 0));
	}



	@Bean
	public NAFCExperimentState experimentState() {
		NAFCExperimentState state = new NAFCExperimentState();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(trialEventListeners());
		state.setChoiceEventListeners(choiceEventListeners());
		state.seteStimEventListeners(eStimEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(experimentEventListeners());
		state.setTaskDataSource(databaseTaskDataSource());
		state.setTaskDoneCache(classicConfig.taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setDrawingController(drawingController());
		state.setInterTrialInterval(classicConfig.xperInterTrialInterval());
		state.setTimeBeforeFixationPointOn(classicConfig.xperTimeBeforeFixationPointOn());
		state.setTimeAllowedForInitialEyeIn(classicConfig.xperTimeAllowedForInitialEyeIn());
		state.setRequiredEyeInHoldTime(classicConfig.xperRequiredEyeInHoldTime());
		state.setDoEmptyTask(classicConfig.xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(classicConfig.xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
		//Target Stuff
		state.setSampleLength(xperSampleLength());
		state.setTargetSelector(eyeTargetSelector());
		state.setTimeAllowedForInitialTargetSelection(xperTimeAllowedForInitialTargetSelection());
		state.setRequiredTargetSelectionHoldTime(xperRequiredTargetSelectionHoldTime());
		state.setTargetSelectionStartDelay(xperTargetSelectionEyeMonitorStartDelay());
		state.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		return state;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<ExperimentEventListener> experimentEventListeners () {
		List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
		listeners.add(messageDispatcher());
		listeners.add(classicConfig.databaseTaskDataSourceController());
		listeners.add(classicConfig.messageDispatcherController());
		listeners.add(classicConfig.dataAcqController());
		listeners.add(classicConfig.eyeZeroLogger());
		listeners.add(classicConfig.experimentCpuBinder());
		listeners.add(intanStimController());
		return listeners;
	}


	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
		trialEventListener.add(eyeMonitorController());
		trialEventListener.add(classicConfig.trialEventLogger());
		trialEventListener.add(classicConfig.experimentProfiler());
		trialEventListener.add(messageDispatcher());
		trialEventListener.add(classicConfig.trialSyncController());
		trialEventListener.add(classicConfig.dataAcqController());
		trialEventListener.add(classicConfig.jvmManager());
		if (!acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			trialEventListener.add(classicConfig.dynamicJuiceUpdater());
		}
		trialEventListener.add(intanStimController());
		return trialEventListener;
	}

	@Bean
	NAFCEyeMonitorController eyeMonitorController(){
		NAFCEyeMonitorController eyeMonitorController = new NAFCEyeMonitorController();
		eyeMonitorController.setEyeSampler(classicConfig.eyeSampler());
		eyeMonitorController.setEyeWindowAdjustable(classicConfig.eyeWindowAdjustables());
		eyeMonitorController.setEyeDeviceWithAdjustableZero(classicConfig.eyeZeroAdjustables());
		return eyeMonitorController;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<ChoiceEventListener> choiceEventListeners () {
		List<ChoiceEventListener> listeners = new LinkedList<ChoiceEventListener>();
		listeners.add(messageDispatcher());
		listeners.add(juiceController());
		listeners.add(intanStimController());
		return listeners;
	}


	@Bean
	public NAFCExperimentMessageDispatcher messageDispatcher() {
		NAFCExperimentMessageDispatcher dispatcher = new NAFCExperimentMessageDispatcher();
		dispatcher.setHost(classicConfig.experimentHost);
		dispatcher.setDbUtil(allenDbUtil());
		return dispatcher;
	}

	@Bean
	public ChoiceEventListener juiceController() {
		NAFCJuiceController controller = new NAFCJuiceController();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			controller.setJuice(new NullDynamicJuice());
		} else {
			controller.setJuice(classicConfig.xperDynamicJuice());
		}
		controller.setChoiceCorrectMultiplier(xperChoiceCorrectJuiceMultiplier());
		controller.setChoiceCorrectMultiplierChance(xperChoiceCorrectJuiceMultiplierChance());
		return controller;
	}

	@Bean
	public int xperChoiceCorrectJuiceMultiplier() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_choice_correct_juice_multiplier", 0));
	}

	@Bean
	public double xperChoiceCorrectJuiceMultiplierChance() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_choice_correct_juice_multiplier_chance", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EStimEventListener> eStimEventListeners(){
		List<EStimEventListener> listeners = new LinkedList<EStimEventListener>();
		listeners.add((EStimEventListener) messageDispatcher());
		listeners.add(intanStimController());
		return listeners;
	}

	@Bean
	public NAFCTrialTriggerIntanStimulationRecordingController intanStimController() {
		NAFCTrialTriggerIntanStimulationRecordingController intanController = new NAFCTrialTriggerIntanStimulationRecordingController();
		intanController.seteStimEnabled(intanConfig.intanEStimEnabled);
		intanController.setIntan(intanConfig.intan());
		intanController.setRecordingEnabled(intanConfig.intanRecordingEnabled());
		intanController.setFileNamingStrategy(rhdConfig.intanFileNamingStrategy());
		return intanController;
	}


	@Bean
	public NAFCTrialDrawingController drawingController() {
		NAFCMarkStimTrialDrawingController controller;
		if (markEveryStep) {
			controller = new NAFCMarkEveryStepTrialDrawingController();
		} else {
			controller = new NAFCMarkStimTrialDrawingController();
		}
		controller.setWindow(classicConfig.monkeyWindow());
		controller.setTaskScene(taskScene());
		controller.setFixationOnWithStimuli(classicConfig.xperFixationOnWithStimuli());
		controller.setScreenShotter(screenShotter());
		return controller;
	}

	@Bean
	public ScreenShotter screenShotter(){
		ScreenShotter screenShotter = new ScreenShotter();
		screenShotter.setEnabled(screenShotEnabled);
		screenShotter.setDirectory(screenShotDirectory);
		screenShotter.setScreenWidthPixels(3840);
		screenShotter.setScreenHeightPixels(2160);
		return screenShotter;

	}

	@Bean
	public NAFCTaskScene taskScene() {
		NAFCGaussScene scene = new NAFCGaussScene();
		scene.setRenderer(experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		scene.setBackgroundColor(classicConfig.xperBackgroundColor());
		return scene;
	}


	/**
	 * Involved in both fixation point eye selection for this code &  choice target selection
	 * @return
	 */
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

	//TODO
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
	public Boolean xperShowAnswer(){
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_nafc_show_answer",0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperRepeatIncorrectTrials(){
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_nafc_repeat_incorrect_trials",0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperRepeatSampleFailTrials(){
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_nafc_repeat_sample_fail_trials",0));
	}
	/**
	 * For fixation point eye selection, not alternative choices.
	 * @return
	 */
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTargetSelectionEyeInTimeThreshold() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_target_selection_eye_in_time_threshold", 0));
	}
	/**
	 * CHANGE THIS for changing amount of time given to choose an alternative target
	 * @return
	 */
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperTimeAllowedForInitialTargetSelection() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_time_allowed_for_initial_target_selection", 0));
	}
	/**
	 * CHANGE THIS for changing amount of time needed to fixate in order to choose an alternative target
	 * @return
	 */
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Long xperRequiredTargetSelectionHoldTime() {
		return Long.parseLong(baseConfig.systemVariableContainer().get("xper_required_target_selection_hold_time", 0));
	}
	/**
	 * For fixation point eye selection, not alternative choices.
	 * @return
	 */
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

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperSampleLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_sample_length", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperShowAnswerLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_answer_length", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public UngetPolicy xperUngetPolicy(){
		return UngetPolicy.valueOf(baseConfig.systemVariableContainer().get("xper_unget_policy",0));
	}

}