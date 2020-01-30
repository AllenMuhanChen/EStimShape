package org.xper.config;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedList;
import java.util.List;
import java.util.Set;

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
import org.xper.acq.SocketDataAcqClient;
import org.xper.acq.comedi.ComediAnalogSWOutDevice;
import org.xper.acq.comedi.ComediAnalogSamplingDevice;
import org.xper.acq.comedi.ComediDigitalPortOutDevice;
import org.xper.acq.mock.SocketSamplingDeviceClient;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.acq.ni.NiAnalogSWOutDevice;
import org.xper.acq.ni.NiAnalogSamplingDevice;
import org.xper.acq.ni.NiDigitalPortOutDevice;
import org.xper.acq.vo.ComediChannelSpec;
import org.xper.acq.vo.NiChannelSpec;
import org.xper.classic.DataAcqController;
import org.xper.classic.DynamicJuiceUpdater;
import org.xper.classic.ExperimentProfiler;
import org.xper.classic.EyeMonitorController;
import org.xper.classic.JuiceController;
import org.xper.classic.TrialSyncController;
import org.xper.classic.JvmManager;
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideEventLogger;
import org.xper.classic.SlideTrialExperiment;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.classic.TrialEventLogger;
import org.xper.classic.TrialExperimentConsoleRenderer;
import org.xper.classic.TrialExperimentEyeController;
import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.TrialExperimentMessageHandler;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentConsoleModel;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.console.MessageReceiverEventListener;
import org.xper.drawing.BlankTaskScene;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.AlternatingScreenMarker;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.FixationPoint;
import org.xper.drawing.object.MonkeyWindow;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.exception.ExperimentSetupException;
import org.xper.experiment.BatchTaskDoneCache;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.experiment.Experiment;
import org.xper.experiment.ExperimentRunner;
import org.xper.experiment.ExperimentRunnerClient;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.TaskDoneCache;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.experiment.listener.CpuBinder;
import org.xper.experiment.listener.DatabaseTaskDataSourceController;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.experiment.listener.EyeZeroLogger;
import org.xper.experiment.listener.MessageDispatcherController;
import org.xper.eye.DefaultEyeMonitor;
import org.xper.eye.DefaultEyeSampler;
import org.xper.eye.EyeDevice;
import org.xper.eye.IscanDevice;
import org.xper.eye.listener.EyeDeviceMessageListener;
import org.xper.eye.listener.EyeEventListener;
import org.xper.eye.listener.EyeEventLogger;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.mapping.LinearMappingAlgorithm;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyeDeviceChannelSpec;
import org.xper.eye.vo.EyeDeviceIdChannelPair;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.eye.win.EyeWindowAdjustable;
import org.xper.eye.win.EyeWindowMessageListener;
import org.xper.eye.win.RampEyeWindowAlgorithm;
import org.xper.eye.zero.EyeZeroAdjustable;
import org.xper.eye.zero.EyeZeroMessageListener;
import org.xper.eye.zero.MovingAverageEyeZeroAlgorithm;
import org.xper.juice.AnalogJuice;
import org.xper.juice.DynamicJuice;
import org.xper.juice.mock.NullDynamicJuice;
import org.xper.trialsync.AnalogTrialSync;
import org.xper.trialsync.mock.NullTrialSync;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(AcqConfig.class)
public class ClassicConfig {
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	
	@ExternalValue("console.eye_simulation")
	public boolean consoleEyeSimulation;
	
	@ExternalValue("console.host")
	public String consoleHost;
	
	@ExternalValue("experiment.cpu")
	public Integer experimentCpu;
	
	@ExternalValue("experiment.monkey_window_fullscreen")
	public boolean monkeyWindowFullScreen;
	
	@ExternalValue("experiment.mark_every_step")
	public boolean markEveryStep;
	
	@ExternalValue("experiment.host")
	public String experimentHost;
	
	@ExternalValue("experiment.acq_offline")
	public boolean experimentAcqOffline;
	
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
	public ExperimentConsole experimentConsole () {
		ExperimentConsole console = new ExperimentConsole();
		
		console.setPaused(xperExperimentInitialPause());
		console.setConsoleRenderer(consoleRenderer());
		console.setMonkeyScreenDimension(monkeyWindow().getScreenDimension());
		console.setModel(experimentConsoleModel());
		console.setCanvasScaleFactor(3);
		
		ExperimentMessageReceiver receiver = messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	
	@Bean
	public ExperimentMessageReceiver messageReceiver () {
		ExperimentMessageReceiver receiver = new ExperimentMessageReceiver();
		receiver.setReceiverHost(consoleHost);
		receiver.setDispatcherHost(experimentHost);
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
		eyeMappingAlgorithm.put(xperLeftIscanId(), leftIscanMappingAlgorithm());
		eyeMappingAlgorithm.put(xperRightIscanId(), rightIscanMappingAlgorithm());
		model.setEyeMappingAlgorithm(eyeMappingAlgorithm);
		
		model.setExperimentRunnerClient(experimentRunnerClient());
		model.setChannelMap(iscanChannelMap());
		model.setMessageHandler(messageHandler());
		
		if (consoleEyeSimulation || acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			// socket sampling server for eye simulation
			SocketSamplingDeviceServer server = new SocketSamplingDeviceServer();
			server.setHost(consoleHost);
			server.setSamplingDevice(model);
			HashMap<Integer, Double> data = new HashMap<Integer, Double>();
			data.put(xperLeftIscanXChannel(), new Double(0));
			data.put(xperLeftIscanYChannel(), new Double(0));
			data.put(xperRightIscanXChannel(), new Double(0));
			data.put(xperRightIscanYChannel(), new Double(0));
			server.setCurrentChannelData(data);
			
			model.setSamplingServer(server);
		}
		return model;
	}
	
	@Bean
	public ExperimentRunner experimentRunner () {
		ExperimentRunner runner = new ExperimentRunner();
		runner.setHost(experimentHost);
		runner.setExperiment(experiment());
		return runner;
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
		state.setSlideEventListeners(slideEventListeners());
		state.setEyeController(eyeController());
		state.setExperimentEventListeners(experimentEventListeners());
		state.setTaskDataSource(taskDataSource());
		state.setTaskDoneCache(taskDoneCache());
		state.setGlobalTimeClient(acqConfig.timeClient());
		state.setDrawingController(drawingController());
		state.setInterTrialInterval(xperInterTrialInterval());
		state.setTimeBeforeFixationPointOn(xperTimeBeforeFixationPointOn());
		state.setTimeAllowedForInitialEyeIn(xperTimeAllowedForInitialEyeIn());
		state.setRequiredEyeInHoldTime(xperRequiredEyeInHoldTime());
		state.setSlidePerTrial(xperSlidePerTrial());
		state.setSlideLength(xperSlideLength());
		state.setInterSlideInterval(xperInterSlideInterval());
		state.setDoEmptyTask(xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(xperDelayAfterTrialComplete());
		return state;
	}
	
	@Bean
	public TaskDoneCache taskDoneCache () {
		BatchTaskDoneCache cache = new BatchTaskDoneCache(10);
		cache.setDbUtil(baseConfig.dbUtil());
		return cache;
	}
	
	@Bean
	public TaskDataSource taskDataSource() {
		return databaseTaskDataSource();
	}
	
	@Bean
	public DatabaseTaskDataSource databaseTaskDataSource () {
		DatabaseTaskDataSource source = new DatabaseTaskDataSource();
		source.setDbUtil(baseConfig.dbUtil());
		source.setQueryInterval(1000);
		source.setUngetBehavior(UngetPolicy.HEAD);
		return source;
	}
	
	@Bean 
	public DatabaseTaskDataSourceController databaseTaskDataSourceController () {
		DatabaseTaskDataSourceController controller = new DatabaseTaskDataSourceController();
		controller.setTaskDataSource(databaseTaskDataSource());
		return controller;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<ExperimentEventListener> experimentEventListeners () {
		List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
		listeners.add(messageDispatcher());
		listeners.add(databaseTaskDataSourceController());
		listeners.add(messageDispatcherController());
		listeners.add(dataAcqController());
		listeners.add(eyeZeroLogger());
		listeners.add(experimentCpuBinder());
		return listeners;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<SlideEventListener> slideEventListeners () {
		List<SlideEventListener> listeners = new LinkedList<SlideEventListener>();
		listeners.add(slideEventLogger());
		listeners.add(experimentProfiler());
		listeners.add(messageDispatcher());
		return listeners;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
		trialEventListener.add(eyeMonitorController());
		trialEventListener.add(trialEventLogger());
		trialEventListener.add(experimentProfiler());
		trialEventListener.add(messageDispatcher());
		trialEventListener.add(juiceController());
		trialEventListener.add(trialSyncController());
		trialEventListener.add(dataAcqController());
		trialEventListener.add(jvmManager());
		if (!acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			trialEventListener.add(dynamicJuiceUpdater());
		}
		
		return trialEventListener;
	}
	
	@Bean
	public JvmManager jvmManager() {
		JvmManager manager = new JvmManager();
		manager.setLocalTimeUtil(baseConfig.localTimeUtil());
		return manager;
	}
	
	@Bean
	public DataAcqController dataAcqController() {
		DataAcqController controller = new DataAcqController();
		controller.setAcqDeviceController(dataAcqClient());
		controller.setOffline(acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE));
		return controller;
	}
	
	@Bean
	public SocketDataAcqClient dataAcqClient() {
		SocketDataAcqClient client = new SocketDataAcqClient(acqConfig.acqServerHost);
		return client;
	}
	
	@Bean
	public TrialDrawingController drawingController() {
		MarkStimTrialDrawingController controller;
		if (markEveryStep) {
			controller = new MarkEveryStepTrialDrawingController();
		} else {
			controller = new MarkStimTrialDrawingController();
		}
		controller.setWindow(monkeyWindow());
		controller.setTaskScene(taskScene());
		controller.setFixationOnWithStimuli(xperFixationOnWithStimuli());
		return controller;
	}
	
	@Bean
	public TrialEventListener juiceController() {
		JuiceController controller = new JuiceController();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			controller.setJuice(new NullDynamicJuice());
		} else {
			controller.setJuice(xperDynamicJuice());
		}
		return controller;
	}
	
	@Bean
	public TrialEventListener trialSyncController() {
		TrialSyncController controller = new TrialSyncController();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			controller.setTrialSync(new NullTrialSync());
		} else {
			controller.setTrialSync(xperTrialSync());
		}
		return controller;
	}
	
	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(xperMonkeyScreenDistance());
		renderer.setDepth(xperMonkeyScreenDepth());
		renderer.setHeight(xperMonkeyScreenHeight());
		renderer.setWidth(xperMonkeyScreenWidth());
		renderer.setPupilDistance(xperMonkeyPupilDistance());
		return renderer;
	}
	
	@Bean
	public AlternatingScreenMarker screenMarker() {
		AlternatingScreenMarker marker = new AlternatingScreenMarker();
		marker.setSize(xperScreenMarkerSize());
		marker.setViewportIndex(xperScreenMarkerViewportIndex());
		return marker;
	}
	
	@Bean
	public TrialExperimentConsoleRenderer consoleRenderer () {
		TrialExperimentConsoleRenderer renderer = new TrialExperimentConsoleRenderer();
		renderer.setMessageHandler(messageHandler());
		renderer.setFixation(consoleFixationPoint());
		renderer.setRenderer(consoleGLRenderer());
		renderer.setBlankScreen(new BlankScreen());
		renderer.setCircle(new Circle());
		renderer.setSquare(new Square());
		return renderer;
	}
	
	@Bean
	public FixationPoint consoleFixationPoint() {
		FixationPoint fixation = new FixationPoint();
		fixation.setColor(new RGBColor(1,1,0));
		fixation.setSize(xperFixationPointSize());
		fixation.setFixationPosition(xperFixationPosition());
		return fixation;
	}
	
	@Bean
	public AbstractRenderer consoleGLRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(xperMonkeyScreenDistance());
		renderer.setDepth(xperMonkeyScreenDepth());
		renderer.setHeight(xperMonkeyScreenHeight());
		renderer.setWidth(xperMonkeyScreenWidth());
		renderer.setPupilDistance(xperMonkeyPupilDistance());
		return renderer;
	}
	
	@Bean
	public TrialExperimentMessageHandler  messageHandler() {
		TrialExperimentMessageHandler messageHandler = new TrialExperimentMessageHandler();
		HashMap<String, EyeDeviceReading> eyeDeviceReading = new HashMap<String, EyeDeviceReading>();
		eyeDeviceReading.put(xperLeftIscanId(), zeroEyeDeviceReading());
		eyeDeviceReading.put(xperRightIscanId(), zeroEyeDeviceReading());
		messageHandler.setEyeDeviceReading(eyeDeviceReading);
		messageHandler.setEyeWindow(new EyeWindow(xperEyeWindowCenter(), xperEyeWindowAlgorithmInitialWindowSize()));
		HashMap<String, Coordinates2D> eyeZero = new HashMap<String, Coordinates2D>();
		eyeZero.put(xperLeftIscanId(), xperLeftIscanEyeZero());
		eyeZero.put(xperRightIscanId(), xperRightIscanEyeZero());
		messageHandler.setEyeZero(eyeZero);
		return messageHandler;
	}
	
	@Bean
	public ExperimentRunnerClient experimentRunnerClient() {
		ExperimentRunnerClient client = new ExperimentRunnerClient(experimentHost);
		return client;
	}
	
	@Bean
	public FixationPoint experimentFixationPoint() {
		FixationPoint f = new FixationPoint ();
		f.setColor(xperFixationPointColor());
		f.setFixationPosition(xperFixationPosition());
		f.setSize(xperFixationPointSize());
		return f;
	}
	
	@Bean
	public MonkeyWindow monkeyWindow() {
		MonkeyWindow win = new MonkeyWindow();
		win.setFullscreen(monkeyWindowFullScreen);
		// enable alpha, depth and stencil buffer
		win.setPixelFormat(new PixelFormat(0, 8, 1, 4));
		return win;
	}
	
	@Bean
	public CpuBinder experimentCpuBinder () {
		CpuBinder binder = new CpuBinder();
		Set<Integer> cpuSet = new HashSet<Integer>();
		cpuSet.add(experimentCpu);
		binder.setCpuSet(cpuSet);
		return binder;
	}
	
	@Bean
	public TrialEventLogger trialEventLogger() {
		TrialEventLogger logger = new TrialEventLogger();
		return logger;
	}
	
	@Bean
	public SlideEventLogger slideEventLogger() {
		SlideEventLogger logger = new SlideEventLogger();
		return logger;
	}
	
	@Bean
	public MessageDispatcherController messageDispatcherController() {
		MessageDispatcherController controller = new MessageDispatcherController();
		controller.setMessageDispatcher(messageDispatcher());
		return controller;
	}
	
	@Bean
	public ExperimentProfiler experimentProfiler() {
		ExperimentProfiler profiler = new ExperimentProfiler();
		return profiler;
	}
	
	@Bean
	public EyeMonitorController eyeMonitorController() {
		EyeMonitorController controller = new EyeMonitorController();
		controller.setEyeSampler(eyeSampler());
		controller.setEyeWindowAdjustable(eyeWindowAdjustables());
		controller.setEyeDeviceWithAdjustableZero(eyeZeroAdjustables());
		return controller;
	}
	
	@Bean
	public SocketSamplingDeviceClient samplingDeviceClient() {
		SocketSamplingDeviceClient client = new SocketSamplingDeviceClient(consoleHost);
		client.setLocalTimeUtil(baseConfig.localTimeUtil());
		return client;
	}
	
	@Bean
	public DefaultEyeSampler eyeSampler() {
		DefaultEyeSampler sampler = new DefaultEyeSampler();
		sampler.setEyeDevice(eyeSamplerDevices());
		if (consoleEyeSimulation || acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			sampler.setAcqSamplingDevice(samplingDeviceClient());
		} else {
			if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NI)) {
				sampler.setAcqSamplingDevice(niAnalogSamplingDevice());
			} else if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_COMEDI)) {
				sampler.setAcqSamplingDevice(comediAnalogSamplingDevice());
			} else {
				throw new ExperimentSetupException("Acq driver " + acqConfig.acqDriverName + " not supported.");
			}
		}
		sampler.setSampleListeners(eyeSamplerEventListeners());
		sampler.setSamplingInterval(xperEyeSamplingInterval());
		sampler.setLocalTimeUtil(baseConfig.localTimeUtil());
		return sampler;
	}
	
	@Bean
	public NiAnalogSamplingDevice niAnalogSamplingDevice() {
		NiAnalogSamplingDevice device = new NiAnalogSamplingDevice();
		device.setLocalTimeUtil(baseConfig.localTimeUtil());
		device.setDeviceString(xperDevice());
		List<NiChannelSpec> inputChannels = new LinkedList<NiChannelSpec>();
		inputChannels.add(xperLeftIscanXChannelNiSpec());
		inputChannels.add(xperLeftIscanYChannelNiSpec());
		inputChannels.add(xperRightIscanXChannelNiSpec());
		inputChannels.add(xperRightIscanYChannelNiSpec());
		device.setInputChannels(inputChannels);
		return device;
	}
	
	@Bean
	public ComediAnalogSamplingDevice comediAnalogSamplingDevice() {
		ComediAnalogSamplingDevice device = new ComediAnalogSamplingDevice();
		device.setLocalTimeUtil(baseConfig.localTimeUtil());
		device.setDeviceString(xperDevice());
		List<ComediChannelSpec> inputChannels = new LinkedList<ComediChannelSpec>();
		inputChannels.add(xperLeftIscanXChannelComediSpec());
		inputChannels.add(xperLeftIscanYChannelComediSpec());
		inputChannels.add(xperRightIscanXChannelComediSpec());
		inputChannels.add(xperRightIscanYChannelComediSpec());
		device.setInputChannels(inputChannels);
		return device;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public HashMap<String, EyeDevice> eyeSamplerDevices () {
		HashMap<String, EyeDevice> devices = new HashMap<String, EyeDevice> ();
		devices.put(xperLeftIscanId(), leftIscan());
		devices.put(xperRightIscanId(), rightIscan());
		return devices;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<EyeSamplerEventListener> eyeSamplerEventListeners () {
		List<EyeSamplerEventListener> sampleListeners = new LinkedList<EyeSamplerEventListener>();
		sampleListeners.add(eyeMonitor());
		return sampleListeners;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<EyeZeroAdjustable> eyeZeroAdjustables () {
		List<EyeZeroAdjustable> adjustables = new LinkedList<EyeZeroAdjustable>();
		adjustables.add(leftIscan());
		adjustables.add(rightIscan());
		return adjustables;
	}
	
	@Bean
	public IscanDevice leftIscan() {
		IscanDevice iscan = new IscanDevice();
		iscan.setEyeDeviceMessageListener(eyeDeviceMessageListeners());
		iscan.setEyeZeroMessageListener(eyeZeroMessageListeners());
		iscan.setId(xperLeftIscanId());
		iscan.setChannel(xperLeftIscanChannelSpec());
		iscan.setEyeZero(xperLeftIscanEyeZero());
		iscan.setEyeZeroAlgorithm(leftIscanMovingAverageEyeZeroAlgorithm());
		iscan.setEyeZeroUpdateEnabled(xperLeftIscanEyeZeroUpdateEnabled());
		iscan.setMappingAlgorithm(leftIscanMappingAlgorithm());
		iscan.setLocalTimeUtil(baseConfig.localTimeUtil());
		return iscan;
	}
	
	@Bean
	public IscanDevice rightIscan() {
		IscanDevice iscan = new IscanDevice();
		iscan.setEyeDeviceMessageListener(eyeDeviceMessageListeners());
		iscan.setEyeZeroMessageListener(eyeZeroMessageListeners());
		iscan.setId(xperRightIscanId());
		iscan.setChannel(xperRightIscanChannelSpec());
		iscan.setEyeZero(xperRightIscanEyeZero());
		iscan.setEyeZeroAlgorithm(rightIscanMovingAverageEyeZeroAlgorithm());
		iscan.setEyeZeroUpdateEnabled(xperRightIscanEyeZeroUpdateEnabled());
		iscan.setMappingAlgorithm(rightIscanMappingAlgorithm());
		iscan.setLocalTimeUtil(baseConfig.localTimeUtil());
		return iscan;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeDeviceMessageListener> eyeDeviceMessageListeners () {
		List<EyeDeviceMessageListener> listeners = new LinkedList<EyeDeviceMessageListener>();
		listeners.add(messageDispatcher());
		return listeners;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeZeroMessageListener> eyeZeroMessageListeners () {
		List<EyeZeroMessageListener> listeners = new LinkedList<EyeZeroMessageListener>();
		listeners.add(messageDispatcher());
		listeners.add(eyeZeroLogger());
		return listeners;
	}
	
	@Bean
	public EyeZeroLogger eyeZeroLogger() {
		EyeZeroLogger logger = new EyeZeroLogger();
		logger.setDbUtil(baseConfig.dbUtil());
		logger.setDbVariableMap(xperEyeZeroIdDbVariableMap());
		return logger;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeWindowAdjustable> eyeWindowAdjustables () {
		List<EyeWindowAdjustable> adjustables = new LinkedList<EyeWindowAdjustable>();
		adjustables.add(eyeMonitor());
		return adjustables;
	}
	
	@Bean
	public DefaultEyeMonitor eyeMonitor() {
		DefaultEyeMonitor monitor = new DefaultEyeMonitor ();
		monitor.setEyeWinCenter(xperEyeWindowCenter());
		monitor.setEyeWindowAlgorithm(eyeWindowAlgorithm());
		monitor.setEyeWindowMessageListener(eyeWindowMessageListeners());
		monitor.setEyeEventListener(eyeEventListeners());
		monitor.setEyeInstrategy(eyeInStrategy());
		monitor.setInTimeThreshold(xperEyeMonitorInTimeThreshold());
		monitor.setOutTimeThreshold(xperEyeMonitorOutTimeThreshold());
		monitor.setLocalTimeUtil(baseConfig.localTimeUtil());
		return monitor;
	}
	
	@Bean
	public EyeInStrategy eyeInStrategy () {
		AnyEyeInStategy strategy = new AnyEyeInStategy();
		List<String> devices = new LinkedList<String>();
		devices.add(xperLeftIscanId());
		devices.add(xperRightIscanId());
		strategy.setEyeDevices(devices);
		return strategy;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeEventListener> eyeEventListeners() {
		List<EyeEventListener> listeners = new LinkedList<EyeEventListener> ();
		listeners.add(eyeController());
		listeners.add(eyeEventLogger());
		listeners.add(messageDispatcher());
		return listeners;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<EyeWindowMessageListener> eyeWindowMessageListeners () {
		List<EyeWindowMessageListener> listeners = new LinkedList<EyeWindowMessageListener>();
		listeners.add(messageDispatcher());
		return listeners;
	}
	
	@Bean
	public EyeEventLogger eyeEventLogger() {
		EyeEventLogger logger = new EyeEventLogger();
		return logger;
	}
	
	@Bean
	public TrialExperimentMessageDispatcher messageDispatcher() {
		TrialExperimentMessageDispatcher dispatcher = new TrialExperimentMessageDispatcher();
		dispatcher.setHost(experimentHost);
		dispatcher.setDbUtil(baseConfig.dbUtil());
		return dispatcher;
	}
	
	@Bean
	public TrialExperimentEyeController eyeController() {
		TrialExperimentEyeController controller = new TrialExperimentEyeController();
		controller.setLocalTimeUtil(baseConfig.localTimeUtil());
		return controller;
	}
	
	@Bean
	public RampEyeWindowAlgorithm eyeWindowAlgorithm() {
		RampEyeWindowAlgorithm algo = new RampEyeWindowAlgorithm();
		algo.setBaseWindowSize(xperEyeWindowAlgorithmBaseWindowSize());
		algo.setInitialWindowSize(xperEyeWindowAlgorithmInitialWindowSize());
		algo.setRampLength(xperEyeWindowAlgorithmRampLength());
		algo.init();
		
		return algo;
	}
	
	@Bean
	public DynamicJuiceUpdater dynamicJuiceUpdater() {
		DynamicJuiceUpdater updater = new DynamicJuiceUpdater();
		updater.setJuice(xperDynamicJuice());
		updater.setVariableContainer(baseConfig.systemVariableContainer());
		return updater;
	}
	
	@Bean 
	public DynamicJuice xperDynamicJuice() {
		AnalogJuice juice = new AnalogJuice();
		juice.setBonusDelay(xperJuiceBonusDelay());
		juice.setBonusProbability(xperJuiceBonusProbability());
		juice.setDelay(xperJuiceDelay());
		juice.setReward(xperJuiceRewardLength());
		juice.setLocalTimeUtil(baseConfig.localTimeUtil());
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NI)) {
			juice.setDevice(niAnalogJuiceDevice());
		} else if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_COMEDI)) {
			juice.setDevice(comediAnalogJuiceDevice());
		} else {
			throw new ExperimentSetupException("Acq driver " + acqConfig.acqDriverName + " not supported.");
		}
		return juice;
	}
	
	@Bean 
	public AnalogTrialSync xperTrialSync() {
		AnalogTrialSync trialSync = new AnalogTrialSync();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NI)) {
			trialSync.setDevice(niAnalogTrialSyncDevice());
		} else if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_COMEDI)) {
			trialSync.setDbUtil(baseConfig.dbUtil());
			trialSync.setDevice(comediAnalogTrialSyncDevice());
		} else {
			throw new ExperimentSetupException("Acq driver " + acqConfig.acqDriverName + " not supported.");
		}
		return trialSync;
	}
	
	@Bean
	public NiAnalogSWOutDevice niAnalogJuiceDevice() {
		NiAnalogSWOutDevice device = new NiAnalogSWOutDevice();
		device.setDeviceString(xperDevice());
		List<NiChannelSpec> channels = new ArrayList<NiChannelSpec>();
		channels.add(xperNiJuiceChannelSpec());
		device.setOutputChannels(channels);		
		return device;
	}
	
	// --------------------------------
	ComediAnalogSWOutDevice device = new ComediAnalogSWOutDevice();;
	List<ComediChannelSpec> channels = new ArrayList<ComediChannelSpec>();
	
	@Bean
	public ComediAnalogSWOutDevice comediAnalogJuiceDevice() {
		ComediAnalogSWOutDevice device = new ComediAnalogSWOutDevice();;
		List<ComediChannelSpec> channels = new ArrayList<ComediChannelSpec>();
		device.setDeviceString(xperDevice());
		channels.add(xperComediJuiceChannelSpec());
		device.setOutputChannels(channels);		
		return device;
	}

	@Bean
	public ComediAnalogSWOutDevice comediAnalogTrialSyncDevice() {
		ComediAnalogSWOutDevice device = new ComediAnalogSWOutDevice();;
		List<ComediChannelSpec> channels = new ArrayList<ComediChannelSpec>();
		device.setDeviceString(xperDevice());
		channels.add(xperComediTrialSyncChannelSpec());
		device.setOutputChannels(channels);		
		return device;
	}
	
	//--------------------------------
	
	@Bean
	public NiAnalogSWOutDevice niAnalogTrialSyncDevice() {
		NiAnalogSWOutDevice device = new NiAnalogSWOutDevice();
		device.setDeviceString(xperDevice());
		List<NiChannelSpec> channels = new ArrayList<NiChannelSpec>();
		channels.add(xperNiTrialSyncChannelSpec());
		device.setOutputChannels(channels);		
		return device;
	}
	
	@Bean
	public NiDigitalPortOutDevice niDigitalPortJuiceDevice() {
		NiDigitalPortOutDevice device = new NiDigitalPortOutDevice();
		device.setDeviceString(xperDevice());
		List<Integer> ports = new LinkedList<Integer>();
		ports.add(xperJuiceChannel());
		device.setPorts(ports);
		return device;
	}
	
	@Bean
	public ComediDigitalPortOutDevice comediDigitalPortJuiceDevice() {
		ComediDigitalPortOutDevice device = new ComediDigitalPortOutDevice();
		device.setDeviceString(xperDevice());
		List<Integer> ports = new LinkedList<Integer>();
		ports.add(xperJuiceChannel());
		device.setPorts(ports);
		return device;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperRightIscanEyeZeroUpdateEnabled () {
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_right_iscan_eye_zero_update_enabled", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperLeftIscanEyeZeroUpdateEnabled () {
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_left_iscan_eye_zero_update_enabled", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public MovingAverageEyeZeroAlgorithm leftIscanMovingAverageEyeZeroAlgorithm() {
		MovingAverageEyeZeroAlgorithm algo = new MovingAverageEyeZeroAlgorithm(xperLeftIscanEyeZeroAlgorithmSpan());
		algo.setEyeZeroUpdateEyeWinThreshold(xperLeftIscanEyeZeroAlgorithmEyeWindowThreshold());
		algo.setEyeZeroUpdateMinSample(xperLeftIscanEyeZeroAlgorithmMinSample());
		algo.setEyeZeroUpdateEyeWinCenter(xperEyeWindowCenter());
		return algo;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public MovingAverageEyeZeroAlgorithm rightIscanMovingAverageEyeZeroAlgorithm() {
		MovingAverageEyeZeroAlgorithm algo = new MovingAverageEyeZeroAlgorithm(xperRightIscanEyeZeroAlgorithmSpan());
		algo.setEyeZeroUpdateEyeWinThreshold(xperRightIscanEyeZeroAlgorithmEyeWindowThreshold());
		algo.setEyeZeroUpdateMinSample(xperRightIscanEyeZeroAlgorithmMinSample());
		algo.setEyeZeroUpdateEyeWinCenter(xperEyeWindowCenter());
		return algo;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public NiChannelSpec xperLeftIscanXChannelNiSpec() {
		NiChannelSpec spec = new NiChannelSpec();
		spec.setChannel(xperLeftIscanXChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_max_value", 0)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_min_value", 0)));
		
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public ComediChannelSpec xperLeftIscanXChannelComediSpec() {
		ComediChannelSpec spec = new ComediChannelSpec();
		spec.setChannel(xperLeftIscanXChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_max_value", 0)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_min_value", 0)));
		spec.setAref(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_reference", 0));
		
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public NiChannelSpec xperLeftIscanYChannelNiSpec() {
		NiChannelSpec spec = new NiChannelSpec();
		spec.setChannel(xperLeftIscanYChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_max_value", 1)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_min_value", 1)));
		
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public ComediChannelSpec xperLeftIscanYChannelComediSpec() {
		ComediChannelSpec spec = new ComediChannelSpec();
		spec.setChannel(xperLeftIscanYChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_max_value", 1)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_min_value", 1)));
		spec.setAref(baseConfig.systemVariableContainer().get("xper_left_iscan_channel_reference", 1));
		
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public NiChannelSpec xperRightIscanXChannelNiSpec() {
		NiChannelSpec spec = new NiChannelSpec();
		spec.setChannel(xperRightIscanXChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_max_value", 0)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_min_value", 0)));
		
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public ComediChannelSpec xperRightIscanXChannelComediSpec() {
		ComediChannelSpec spec = new ComediChannelSpec();
		spec.setChannel(xperRightIscanXChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_max_value", 0)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_min_value", 0)));
		spec.setAref(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_reference", 0));
		
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public NiChannelSpec xperRightIscanYChannelNiSpec() {
		NiChannelSpec spec = new NiChannelSpec();
		spec.setChannel(xperRightIscanYChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_max_value", 1)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_min_value", 1)));
		
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public ComediChannelSpec xperRightIscanYChannelComediSpec() {
		ComediChannelSpec spec = new ComediChannelSpec();
		spec.setChannel(xperRightIscanYChannel().shortValue());
		spec.setMaxValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_max_value", 1)));
		spec.setMinValue(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_min_value", 1)));
		spec.setAref(baseConfig.systemVariableContainer().get("xper_right_iscan_channel_reference", 1));
		
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperScreenMarkerSize() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_screen_marker_size", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperScreenMarkerViewportIndex() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_screen_marker_viewport_index", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRightIscanEyeZeroAlgorithmEyeWindowThreshold() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_eye_zero_algorithm_eye_window_threshold", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperRightIscanEyeZeroAlgorithmMinSample() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_right_iscan_eye_zero_algorithm_min_sample", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperRightIscanEyeZeroAlgorithmSpan() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_right_iscan_eye_zero_algorithm_span", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperLeftIscanEyeZeroAlgorithmEyeWindowThreshold() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_eye_zero_algorithm_eye_window_threshold", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperLeftIscanEyeZeroAlgorithmMinSample() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_left_iscan_eye_zero_algorithm_min_sample", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperLeftIscanEyeZeroAlgorithmSpan() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_left_iscan_eye_zero_algorithm_span", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperEyeSamplingInterval() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_sampling_interval", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public HashMap<String, String> xperEyeDeviceParameterIdDbVariableMap() {
		HashMap<String, String> map = new HashMap<String, String>();
		map.put(xperLeftIscanId(), "xper_left_iscan_mapping_algorithm_parameter");
		map.put(xperRightIscanId(), "xper_right_iscan_mapping_algorithm_parameter");
		return map;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public HashMap<String, String> xperEyeZeroIdDbVariableMap() {
		HashMap<String, String> map = new HashMap<String, String>();
		map.put(xperLeftIscanId(), "xper_left_iscan_eye_zero");
		map.put(xperRightIscanId(), "xper_right_iscan_eye_zero");
		return map;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperEyeMonitorInTimeThreshold() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_monitor_in_time_threshold", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperEyeMonitorOutTimeThreshold() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_monitor_out_time_threshold", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperEyeWindowAlgorithmInitialWindowSize() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_window_algorithm_initial_window_size", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperEyeWindowAlgorithmRampLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_eye_window_algorithm_ramp_length", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperInterTrialInterval() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_inter_trial_interval", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperDelayAfterTrialComplete() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_delay_after_trial_complete", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperTimeBeforeFixationPointOn() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_time_before_fixation_point_on", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperTimeAllowedForInitialEyeIn() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_time_allowed_for_initial_eye_in", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperRequiredEyeInHoldTime() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_required_eye_in_and_hold_time", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperSlidePerTrial() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_slides_per_trial", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperSlideLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_slide_length", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperInterSlideInterval() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_inter_slide_interval", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperDoEmptyTask() {
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_do_empty_task", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperMonkeyScreenInverted() {
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_monkey_screen_inverted", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public NiChannelSpec xperNiJuiceChannelSpec() {
		NiChannelSpec spec = new NiChannelSpec();
		spec.setChannel(xperJuiceChannel().shortValue());
		spec.setMaxValue(xperJuiceChannelMaxValue());
		spec.setMinValue(xperJuiceChannelMinValue());
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public NiChannelSpec xperNiTrialSyncChannelSpec() {
		NiChannelSpec spec = new NiChannelSpec();
		spec.setChannel(xperTrialSyncChannel().shortValue());
		spec.setMaxValue(xperJuiceChannelMaxValue());
		spec.setMinValue(xperJuiceChannelMinValue());
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public ComediChannelSpec xperComediJuiceChannelSpec() {
		ComediChannelSpec spec = new ComediChannelSpec();
		spec.setChannel(xperJuiceChannel().shortValue()); 
		spec.setMaxValue(xperJuiceChannelMaxValue());
		spec.setMinValue(xperJuiceChannelMinValue());
		spec.setAref(xperJuiceChannelReference());
		return spec;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public ComediChannelSpec xperComediTrialSyncChannelSpec() {
		ComediChannelSpec spec = new ComediChannelSpec();
		spec.setChannel(xperTrialSyncChannel().shortValue());
		spec.setMaxValue(10);
		spec.setMinValue(-10);
		spec.setAref(xperTrialSyncChannelReference());
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperJuiceChannel() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_juice_channel", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperTrialSyncChannel() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_fixation_sync_channel", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public String xperTrialSyncChannelReference() {
		return baseConfig.systemVariableContainer().get("xper_fixation_sync_channel_reference", 0);
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperJuiceChannelMinValue() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_juice_channel_min_value", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public String xperJuiceChannelReference() {
		return baseConfig.systemVariableContainer().get("xper_juice_channel_reference", 0);
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperJuiceChannelMaxValue() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_juice_channel_max_value", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public String xperDevice() {
		return baseConfig.systemVariableContainer().get("xper_device", 0);
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperJuiceDelay() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_juice_delay", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperJuiceRewardLength() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_juice_reward_length", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperJuiceBonusDelay() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_juice_bonus_delay", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperJuiceBonusProbability() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_juice_bonus_probability", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public HashMap<Integer, EyeDeviceIdChannelPair> iscanChannelMap() {
		HashMap<Integer, EyeDeviceIdChannelPair> map = new HashMap<Integer, EyeDeviceIdChannelPair>();
		map.put(xperLeftIscanXChannel(), new EyeDeviceIdChannelPair(xperLeftIscanId(), "X" ));
		map.put(xperLeftIscanYChannel(), new EyeDeviceIdChannelPair(xperLeftIscanId(), "Y" ));
		map.put(xperRightIscanXChannel(), new EyeDeviceIdChannelPair(xperRightIscanId(), "X"));
		map.put(xperRightIscanYChannel(), new EyeDeviceIdChannelPair(xperRightIscanId(), "Y" ));
		return map;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public MappingAlgorithm rightIscanMappingAlgorithm() {
		LinearMappingAlgorithm algorithm = new LinearMappingAlgorithm();
		algorithm.setSxh(xperRightIscanMappingAlgorithmSxh());
		algorithm.setSxv(xperRightIscanMappingAlgorithmSxv());  
		algorithm.setSyh(xperRightIscanMappingAlgorithmSyh());
		algorithm.setSyv(xperRightIscanMappingAlgorithmSyv());
		return algorithm;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRightIscanMappingAlgorithmSxh() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_mapping_algorithm_parameter", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRightIscanMappingAlgorithmSxv() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_mapping_algorithm_parameter", 1));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRightIscanMappingAlgorithmSyh() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_mapping_algorithm_parameter", 2));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperRightIscanMappingAlgorithmSyv() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_mapping_algorithm_parameter", 3));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public LinearMappingAlgorithm leftIscanMappingAlgorithm() {
		LinearMappingAlgorithm a = new LinearMappingAlgorithm();
		a.setSxh(xperLeftIscanMappingAlgorithmSxh());
		a.setSxv(xperLeftIscanMappingAlgorithmSxv());
		a.setSyh(xperLeftIscanMappingAlgorithmSyh());
		a.setSyv(xperLeftIscanMappingAlgorithmSyv());
		return a;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperLeftIscanMappingAlgorithmSxh() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_mapping_algorithm_parameter", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperLeftIscanMappingAlgorithmSxv() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_mapping_algorithm_parameter", 1));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperLeftIscanMappingAlgorithmSyh() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_mapping_algorithm_parameter", 2));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperLeftIscanMappingAlgorithmSyv() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_mapping_algorithm_parameter", 3));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public EyeDeviceChannelSpec xperRightIscanChannelSpec() {
		EyeDeviceChannelSpec spec = new EyeDeviceChannelSpec();
		spec.setX(Integer.parseInt(baseConfig.systemVariableContainer().get("xper_right_iscan_channel", 0)));
		spec.setY(Integer.parseInt(baseConfig.systemVariableContainer().get("xper_right_iscan_channel", 1)));
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperRightIscanXChannel() {
		return xperRightIscanChannelSpec().getX();
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperRightIscanYChannel() {
		return xperRightIscanChannelSpec().getY();
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperLeftIscanXChannel() {
		return xperLeftIscanChannelSpec().getX();
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperLeftIscanYChannel() {
		return xperLeftIscanChannelSpec().getY();
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public EyeDeviceChannelSpec xperLeftIscanChannelSpec() {
		EyeDeviceChannelSpec spec = new EyeDeviceChannelSpec();
		spec.setX(Integer.parseInt(baseConfig.systemVariableContainer().get("xper_left_iscan_channel", 0)));
		spec.setY(Integer.parseInt(baseConfig.systemVariableContainer().get("xper_left_iscan_channel", 1)));
		return spec;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperMonkeyScreenDistance() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_distance", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperMonkeyPupilDistance() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_pupil_distance", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperMonkeyScreenWidth() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_width", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperMonkeyScreenHeight() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_height", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperMonkeyScreenDepth() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_monkey_screen_depth", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Coordinates2D xperFixationPosition() {
		Coordinates2D pos = new Coordinates2D();
		pos.setX(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_fixation_position", 0)));
		pos.setY(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_fixation_position", 1)));
		return pos;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperFixationPointSize() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_fixation_point_size", 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public RGBColor xperFixationPointColor() {
		RGBColor color = new RGBColor();
		color.setRed(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_fixation_point_color", 0)));
		color.setGreen(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_fixation_point_color", 1)));
		color.setBlue(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_fixation_point_color", 2)));
		return color;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public boolean xperExperimentInitialPause() {
		return true;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Coordinates2D xperRightIscanEyeZero() {
		Coordinates2D pos = new Coordinates2D();
		pos.setX(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_eye_zero", 0)));
		pos.setY(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_right_iscan_eye_zero", 1)));
		return pos;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Coordinates2D xperLeftIscanEyeZero() {
		Coordinates2D pos = new Coordinates2D();
		pos.setX(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_eye_zero", 0)));
		pos.setY(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_left_iscan_eye_zero", 1)));
		return pos;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public String xperLeftIscanId() {
		return "leftIscan";
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public String xperRightIscanId() {
		return "rightIscan";
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public EyeDeviceReading zeroEyeDeviceReading() {
		return new EyeDeviceReading(new Coordinates2D(0, 0), new Coordinates2D(0, 0));
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Coordinates2D xperEyeWindowCenter() {
		Coordinates2D pos = new Coordinates2D();
		pos.setX(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_window_center", 0)));
		pos.setY(Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_window_center", 1)));
		return pos;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Double xperEyeWindowAlgorithmBaseWindowSize() {
		return Double.parseDouble(baseConfig.systemVariableContainer().get("xper_eye_window_algorithm_base_window_size", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Boolean xperFixationOnWithStimuli() {
		return Boolean.parseBoolean(baseConfig.systemVariableContainer().get("xper_fixation_on_with_stimuli", 0));
	}

	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public RGBColor xperStimColorBackground() {
		RGBColor bColor = new RGBColor();
		bColor.setRed(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_stim_color_background", 0)));
		bColor.setGreen(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_stim_color_background", 1)));
		bColor.setBlue(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_stim_color_background", 2)));
		return bColor;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public RGBColor xperStimColorForeground() {
		RGBColor fColor = new RGBColor();
		fColor.setRed(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_stim_color_foreground", 0)));
		fColor.setGreen(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_stim_color_foreground", 1)));
		fColor.setBlue(Float.parseFloat(baseConfig.systemVariableContainer().get("xper_stim_color_foreground", 2)));
		return fColor;
	}
	
}