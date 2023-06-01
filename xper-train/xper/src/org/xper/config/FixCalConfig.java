package org.xper.config;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.classic.TrialEventListener;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.classic.EyeMonitorController;
import org.xper.classic.SlideTrialExperiment;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentConsoleModel;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.console.MessageReceiverEventListener;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.FixationPoint;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.exception.ExperimentSetupException;
import org.xper.experiment.Experiment;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.experiment.listener.MessageDispatcherController;
import org.xper.experiment.mock.NullTaskDataSource;
import org.xper.experiment.mock.NullTaskDoneCache;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.eye.listener.EyeEventListener;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.strategy.StereoEyeInStrategy;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.eye.win.EyeWindowMessageListener;
import org.xper.eye.zero.EyeZeroAdjustable;
import org.xper.fixcal.FixCalConsoleRenderer;
import org.xper.fixcal.FixCalEventListener;
import org.xper.fixcal.FixCalMessageDispatcher;
import org.xper.fixcal.FixCalMessageHandler;
import org.xper.fixcal.FixationCalibration;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class FixCalConfig {
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;

	@ExternalValue("fixcal.screen_setup")
	public String fixcalScreenSetup;

	@Bean
	public EyeInStrategy eyeInStrategy () {
		StereoEyeInStrategy strategy = new StereoEyeInStrategy();
		strategy.setLeftDeviceId(classicConfig.xperLeftIscanId());
		strategy.setRightDeviceId(classicConfig.xperRightIscanId());
		return strategy;
	}

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
		state.setTrialEventListeners(trialEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.setEyeController(classicConfig.eyeController());
		state.setExperimentEventListeners(experimentEventListeners());
		state.setTaskDataSource(taskDataSource());
		state.setTaskDoneCache(taskDoneCache());
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
	public FixationCalibration taskScene() {
		FixationCalibration scene = new FixationCalibration();
		scene.setFixation(experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setRenderer(classicConfig.experimentGLRenderer());
		scene.setCalibrationDegree(5.0);
		scene.setFixationPoint(experimentFixationPoint());
		scene.setEyeMonitor(classicConfig.eyeMonitor());
		scene.setDeviceDbVariableMap(classicConfig.xperEyeDeviceParameterIdDbVariableMap());
		scene.setEyeZeroDbVariableMap(classicConfig.xperEyeZeroIdDbVariableMap());
		List<FixCalEventListener> fixCalEventListeners = new LinkedList<FixCalEventListener>();
		fixCalEventListeners.add(messageDispatcher());
		scene.setFixCalEventListeners(fixCalEventListeners);
		scene.setDbUtil(baseConfig.dbUtil());
		return scene;
	}

	@Bean
	public AbstractRenderer experimentGLRenderer () {
		if (fixcalScreenSetup.equalsIgnoreCase("stereo")) {
			PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
			renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
			renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
			renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
			renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
			renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
			renderer.setInverted(classicConfig.xperMonkeyScreenInverted());
			return renderer;
		} else if (fixcalScreenSetup.equalsIgnoreCase("mono")){
			PerspectiveRenderer renderer = new PerspectiveRenderer();
			renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
			renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
			renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
			renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
			renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
			return renderer;
		} else {
			throw new ExperimentSetupException("Invalid screen setup: " + fixcalScreenSetup);
		}
	}

	@Bean
	public FixationPoint experimentFixationPoint() {
		FixationPoint f = new FixationPoint ();
		f.setColor(classicConfig.xperFixationPointColor());
		f.setSize(classicConfig.xperFixationPointSize());
		return f;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperRightIscanEyeZeroUpdateEnabled () {
		return false;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperLeftIscanEyeZeroUpdateEnabled () {
		return false;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperFixationOnWithStimuli() {
		return true;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeDeviceMessageListener> eyeDeviceMessageListeners () {
		List<EyeDeviceMessageListener> listeners = new LinkedList<EyeDeviceMessageListener>();
		listeners.add(taskScene());
		listeners.add(messageDispatcher());
		return listeners;
	}

	@Bean
	public NullTaskDoneCache taskDoneCache() {
		return new NullTaskDoneCache();
	}

	@Bean
	public NullTaskDataSource taskDataSource() {
		return new NullTaskDataSource();
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<ExperimentEventListener> experimentEventListeners () {
		List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
		listeners.add(taskScene());
		listeners.add(messageDispatcher());
		listeners.add(messageDispatcherController());
		listeners.add(classicConfig.experimentCpuBinder());
		return listeners;
	}


	@Bean
	public MessageDispatcherController messageDispatcherController() {
		MessageDispatcherController controller = new MessageDispatcherController();
		controller.setMessageDispatcher(messageDispatcher());
		return controller;
	}


	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> listeners = new LinkedList<TrialEventListener>();
		listeners.add(taskScene());
		listeners.add(classicConfig.eyeMonitorController());
		listeners.add(classicConfig.trialEventLogger());
		listeners.add(classicConfig.experimentProfiler());
		listeners.add(messageDispatcher());
		listeners.add(classicConfig.juiceController());
		listeners.add(classicConfig.trialSyncController());
		listeners.add(classicConfig.jvmManager());
		if (!acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			listeners.add(classicConfig.dynamicJuiceUpdater());
		}
		return listeners;
	}



	@Bean
	public FixCalMessageDispatcher messageDispatcher() {
		FixCalMessageDispatcher dispatcher = new FixCalMessageDispatcher();
		dispatcher.setHost(classicConfig.experimentHost);
		dispatcher.setDbUtil(baseConfig.dbUtil());
		return dispatcher;
	}

	@Bean
	public FixCalConsoleRenderer consoleRenderer () {
		FixCalConsoleRenderer renderer = new FixCalConsoleRenderer();
		renderer.setMessageHandler(messageHandler());
		renderer.setFixation(classicConfig.consoleFixationPoint());
		renderer.setRenderer(classicConfig.consoleGLRenderer());
		renderer.setBlankScreen(new BlankScreen());
		renderer.setCircle(new Circle());
		renderer.setSquare(new Square());
		return renderer;
	}

	@Bean
	public FixCalMessageHandler messageHandler () {
		FixCalMessageHandler messageHandler = new FixCalMessageHandler();
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
	public ExperimentMessageReceiver messageReceiver () {
		ExperimentMessageReceiver receiver = new ExperimentMessageReceiver();
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
	public ExperimentConsoleModel experimentConsoleModel () {
		ExperimentConsoleModel model = new ExperimentConsoleModel();
		model.setMessageReceiver(messageReceiver());
		model.setLocalTimeUtil(baseConfig.localTimeUtil());

		HashMap<String, MappingAlgorithm> eyeMappingAlgorithm = new HashMap<String, MappingAlgorithm>();
		eyeMappingAlgorithm.put(classicConfig.xperLeftIscanId(), classicConfig.leftIscanMappingAlgorithm());
		eyeMappingAlgorithm.put(classicConfig.xperRightIscanId(), classicConfig.rightIscanMappingAlgorithm());
		model.setEyeMappingAlgorithm(eyeMappingAlgorithm);

		model.setExperimentRunnerClient(classicConfig.experimentRunnerClient());
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

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeWindowMessageListener> eyeWindowMessageListeners () {
		List<EyeWindowMessageListener> listeners = new LinkedList<EyeWindowMessageListener>();
		listeners.add(messageDispatcher());
		return listeners;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeEventListener> eyeEventListeners() {
		List<EyeEventListener> listeners = new LinkedList<EyeEventListener> ();
		listeners.add(classicConfig.eyeController());
		listeners.add(classicConfig.eyeEventLogger());
		listeners.add(messageDispatcher());
		return listeners;
	}


}