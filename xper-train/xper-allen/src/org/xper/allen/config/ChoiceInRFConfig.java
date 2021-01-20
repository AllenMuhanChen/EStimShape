package org.xper.allen.config;


import java.beans.PropertyVetoException;
import java.util.HashMap;
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
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.allen.experiment.saccade.console.SaccadeExperimentConsole;
import org.xper.allen.experiment.saccade.console.SaccadeExperimentConsoleModel;
import org.xper.allen.experiment.saccade.console.SaccadeExperimentConsoleRenderer;
import org.xper.allen.experiment.saccade.console.SaccadeExperimentMessageHandler;
import org.xper.allen.experiment.twoac.ChoiceEventListener;
import org.xper.allen.experiment.twoac.ChoiceInRFTrialExperiment;
import org.xper.allen.experiment.twoac.TwoACDatabaseTaskDataSource;
import org.xper.allen.experiment.twoac.TwoACExperimentMessageDispatcher;
import org.xper.allen.experiment.twoac.TwoACExperimentState;
import org.xper.allen.experiment.twoac.TwoACGaussScene;
import org.xper.allen.experiment.twoac.TwoACJuiceController;
import org.xper.allen.experiment.twoac.TwoACMarkEveryStepTrialDrawingController;
import org.xper.allen.experiment.twoac.TwoACMarkStimTrialDrawingController;
import org.xper.allen.experiment.twoac.TwoACTaskScene;
import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.allen.util.AllenDbUtil;
import org.xper.allen.util.AllenXMLUtil;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.BlankTaskScene;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.object.Circle;
import org.xper.drawing.object.Square;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.exception.DbException;
import org.xper.experiment.ExperimentRunner;
import org.xper.experiment.DatabaseTaskDataSource.UngetPolicy;
import org.xper.eye.RobustEyeTargetSelector;
import org.xper.eye.listener.EyeSamplerEventListener;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.juice.mock.NullDynamicJuice;
import org.xper.util.IntanUtil;

import com.mchange.v2.c3p0.ComboPooledDataSource;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class ChoiceInRFConfig {

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
	
	public String getJdbcUrl() {
		return jdbcUrl;
	}
	@Bean
	public IntanUtil intanUtil() {
		IntanUtil iUtil = null;
		try {
		iUtil = new IntanUtil();
		} catch (Exception e) {
			System.out.println("WARNING: IntanUtil could not be initialized");
			//e.printStackTrace();
		}
		return iUtil;
	}
/*	
	@Bean
	public TaskScene taskScene() {
		BlankTaskScene scene = new BlankTaskScene();
		scene.setRenderer(classicConfig.experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		return scene;
	}
*/

	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		
		System.out.println("23108 screen width = " + classicConfig.xperMonkeyScreenWidth());
		
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		renderer.setInverted(classicConfig.xperMonkeyScreenInverted());
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
	public SaccadeExperimentConsole experimentConsole () {
		SaccadeExperimentConsole console = new SaccadeExperimentConsole();
		
		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(consoleRenderer());
		console.setMonkeyScreenDimension(classicConfig.monkeyWindow().getScreenDimension());
		console.setModel(experimentConsoleModel());
		console.setCanvasScaleFactor(3);
		
		ExperimentMessageReceiver receiver = classicConfig.messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	

	@Bean
	public SaccadeExperimentConsoleModel experimentConsoleModel () {
		SaccadeExperimentConsoleModel model = new SaccadeExperimentConsoleModel();
		model.setMessageReceiver(classicConfig.messageReceiver());
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
	
	@Bean
	public SaccadeExperimentConsoleRenderer consoleRenderer () {
		SaccadeExperimentConsoleRenderer renderer = new SaccadeExperimentConsoleRenderer();
		/*
		 * There's a messageHandler and saccadeMessageHandler because I don't know how to overwrite @Bean Dependencies.
		 * This could be reduced to just one method by making on messageHandler that's just copy pasting TrialExperimentMessageHandler with SaccadeExperimentMessageHandler methods inside.
		 */
		renderer.setMessageHandler(classicConfig.messageHandler());
		renderer.setSaccadeMessageHandler(messageHandler());
		renderer.setFixation(classicConfig.consoleFixationPoint());
		renderer.setRenderer(consoleGLRenderer());
		renderer.setBlankScreen(new BlankScreen());
		renderer.setCircle(new Circle());
		renderer.setSquare(new Square());
		return renderer;
	}
	
	//TODO 
	@Bean
	public SaccadeExperimentMessageHandler  messageHandler() {
		SaccadeExperimentMessageHandler messageHandler = new SaccadeExperimentMessageHandler();
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
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth()/2); //AC Change: divide xperMonkeyScreenWidth by 2 to account for two XScreen aspect ratio change. 
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
	public TwoACDatabaseTaskDataSource databaseTaskDataSource() {
		TwoACDatabaseTaskDataSource source = new TwoACDatabaseTaskDataSource();
		source.setDbUtil(allenDbUtil());
		source.setQueryInterval(1000);
		source.setUngetBehavior(UngetPolicy.TAIL);
		return source;
	}
	
	//TODO 
	@Bean
	public ExperimentRunner experimentRunner () {
		ExperimentRunner runner = new ExperimentRunner();
		runner.setHost(classicConfig.experimentHost);
		runner.setExperiment(experiment());
		return runner;
	}
	
	//TODO
	@Bean
	public ChoiceInRFTrialExperiment experiment() {
		ChoiceInRFTrialExperiment xper = new ChoiceInRFTrialExperiment();
		xper.setEyeMonitor(classicConfig.eyeMonitor());
		xper.setStateObject(experimentState());
		xper.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		xper.setDbUtil(allenDbUtil());
		return xper;
	}
	
    //TODO
	@Bean
	public TwoACExperimentState experimentState() {
		TwoACExperimentState state = new TwoACExperimentState();
		state.setLocalTimeUtil(baseConfig.localTimeUtil());
		state.setTrialEventListeners(trialEventListeners());
		state.setChoiceEventListeners(choiceEventListeners());
		state.setSlideEventListeners(classicConfig.slideEventListeners());
		state.seteStimEventListeners(eStimEventListeners());
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
		state.setSampleLength(xperSampleLength());
		state.setChoiceLength(xperChoiceLength());
		state.setDoEmptyTask(classicConfig.xperDoEmptyTask());
		state.setSleepWhileWait(true);
		state.setPause(classicConfig.xperExperimentInitialPause());
		state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
		//Target Stuff
		state.setSampleLength(xperSampleLength());
		state.setChoiceLength(xperChoiceLength());
		state.setTargetSelector(eyeTargetSelector());
		state.setTimeAllowedForInitialTargetSelection(xperTimeAllowedForInitialTargetSelection());  
		state.setRequiredTargetSelectionHoldTime(xperRequiredTargetSelectionHoldTime());
		state.setTargetSelectionStartDelay(xperTargetSelectionEyeMonitorStartDelay());
		state.setBlankTargetScreenDisplayTime(xperBlankTargetScreenDisplayTime());
		//Intan Stuff
		try {
		state.setIntanUtil(intanUtil());
		} catch (Exception e) {
			System.out.println("Cant set IntanUtil");
			
		}
		return state;
	}
	
	//TODO
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
		trialEventListener.add(classicConfig.eyeMonitorController());
		trialEventListener.add(classicConfig.trialEventLogger());
		trialEventListener.add(classicConfig.experimentProfiler());
		trialEventListener.add(messageDispatcher());
		//trialEventListener.add(juiceController());
		trialEventListener.add(classicConfig.trialSyncController());
		trialEventListener.add(classicConfig.dataAcqController());
		trialEventListener.add(classicConfig.jvmManager());
		if (!acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			trialEventListener.add(classicConfig.dynamicJuiceUpdater());
		}
		
		return trialEventListener;
	}
/*
	//TODO
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<TargetEventListener> targetEventListeners () {
		List<TargetEventListener> listeners = new LinkedList<TargetEventListener>();
		listeners.add((TargetEventListener) messageDispatcher());
		listeners.add((TargetEventListener) juiceController());
		return listeners;
	}
	*/
	//TODO
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<ChoiceEventListener> choiceEventListeners () {
		List<ChoiceEventListener> listeners = new LinkedList<ChoiceEventListener>();
		listeners.add(messageDispatcher());
		listeners.add(juiceController());
		return listeners;
	}
	
	
	
	@Bean
	public TwoACExperimentMessageDispatcher messageDispatcher() {
		TwoACExperimentMessageDispatcher dispatcher = new TwoACExperimentMessageDispatcher();
		dispatcher.setHost(classicConfig.experimentHost);
		dispatcher.setDbUtil(allenDbUtil());
		return dispatcher;
	}
	
	@Bean
	public ChoiceEventListener juiceController() {
		TwoACJuiceController controller = new TwoACJuiceController();
		if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			controller.setJuice(new NullDynamicJuice());
		} else {
			controller.setJuice(classicConfig.xperDynamicJuice());
		}
		return controller;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public List<SimpleEStimEventListener> eStimEventListeners(){
		List<SimpleEStimEventListener> listeners = new LinkedList<SimpleEStimEventListener>();
		listeners.add((SimpleEStimEventListener) messageDispatcher());
		return listeners;
	}


	private TrialDrawingController drawingController() {
		MarkStimTrialDrawingController controller;
		if (markEveryStep) {
			controller = new TwoACMarkEveryStepTrialDrawingController();
		} else {
			controller = new TwoACMarkStimTrialDrawingController();
		}
		System.out.println("Setting Window");
		controller.setWindow(classicConfig.monkeyWindow());
		System.out.println("Setting taskSCene");
		controller.setTaskScene(this.taskScene());
		System.out.println("ONE:");
		System.out.println(taskScene().toString());
		System.out.println("TWO:");
		System.out.println(controller.getTaskScene().toString());
		System.out.println("Setting FixaationOnWithStimuli");
		controller.setFixationOnWithStimuli(classicConfig.xperFixationOnWithStimuli());
		return controller;
	}

	
	@Bean
	public TwoACGaussScene taskScene() {
		System.out.println("taskScene called");
		TwoACGaussScene scene = new TwoACGaussScene();
		scene.setRenderer(experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		return scene;
	}
	
	
	//TODO
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

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperSampleLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_sample_length", 0));
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public Integer xperChoiceLength() {
		return Integer.parseInt(baseConfig.systemVariableContainer().get("xper_choice_length", 0));
	}
}

	