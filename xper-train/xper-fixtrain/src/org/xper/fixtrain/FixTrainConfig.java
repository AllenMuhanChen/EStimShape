package org.xper.fixtrain;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.classic.TrialEventListener;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.FixCalConfig;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;
import org.xper.drawing.object.BlankScreen;
import org.xper.experiment.TaskDataSource;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.experiment.listener.MessageDispatcherController;
import org.xper.experiment.mock.NullTaskDataSource;
import org.xper.experiment.mock.NullTaskDoneCache;
import org.xper.eye.vo.EyeDeviceReading;
import org.xper.eye.vo.EyeWindow;
import org.xper.fixcal.FixCalEventListener;
import org.xper.fixcal.FixCalMessageDispatcher;
import org.xper.fixcal.FixCalMessageHandler;
import org.xper.fixtrain.console.FixTrainClient;
import org.xper.fixtrain.console.FixTrainConsolePlugin;
import org.xper.fixtrain.drawing.FixTrainDrawable;
import org.xper.fixtrain.drawing.FixTrainFixationPoint;

import java.util.*;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class FixTrainConfig {
    @Autowired
    ClassicConfig classicConfig;
    @Autowired
    AcqConfig acqConfig;
    @Autowired
    BaseConfig baseConfig;

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
        state.setDoEmptyTask(xperDoEmptyTask());
        state.setSleepWhileWait(true);
        state.setPause(classicConfig.xperExperimentInitialPause());
        state.setDelayAfterTrialComplete(classicConfig.xperDelayAfterTrialComplete());
        return state;
    }

    @Bean
    public FixTrainScene taskScene(){
        FixTrainScene scene = new FixTrainScene();
        scene.setRenderer(classicConfig.experimentGLRenderer());
        scene.setFixation(classicConfig.experimentFixationPoint());
        scene.setBlankScreen(new BlankScreen());
        scene.setMarker(classicConfig.screenMarker());
        scene.setFixTrainObjectMap(fixTrainObjectMap());
        scene.setCalibrationDegree(5.0);
        scene.setEyeMonitor(classicConfig.eyeMonitor());
        scene.setFixCalEventListeners(fixCalEventListeners());
        return scene;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public List<ExperimentEventListener> experimentEventListeners () {
        List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
        listeners.add(taskScene());
        listeners.add(messageDispatcher());
        listeners.add(messageDispatcherController());
        listeners.add(classicConfig.experimentCpuBinder());
        listeners.add(taskDataSourceController());
        return listeners;
    }

    @Bean
    public FixTrainTaskDataSourceController taskDataSourceController(){
        FixTrainTaskDataSourceController controller = new FixTrainTaskDataSourceController();
        controller.setTaskDataSource((FixTrainTaskDataSource) taskDataSource());
        return controller;
    }

    @Bean
    public TaskDataSource taskDataSource() {
        FixTrainTaskDataSource taskDataSource = new FixTrainTaskDataSource();
        taskDataSource.setHost(classicConfig.experimentHost);
        taskDataSource.setFixTrainObjectMap(fixTrainObjectMap());
        return taskDataSource;
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
    public Map<String, FixTrainDrawable> fixTrainObjectMap() {
        Map<String, FixTrainDrawable> map = new LinkedHashMap<>();
        map.put(FixTrainFixationPoint.class.getName(), defaultFixationPoint());
        return map;
    }

    @Bean
    public FixTrainFixationPoint defaultFixationPoint() {
        int size = 10;
        RGBColor color = new RGBColor(1f, 1f, 0f);
        boolean solid = true;

        return new FixTrainFixationPoint(size, color, solid);
    }

    @Bean
    public List<FixCalEventListener> fixCalEventListeners() {
        List<FixCalEventListener> listeners = new ArrayList<>();
        listeners.add(messageDispatcher());
        return listeners;
    }

    @Bean
    public MessageDispatcherController messageDispatcherController() {
        MessageDispatcherController controller = new MessageDispatcherController();
        controller.setMessageDispatcher(messageDispatcher());
        return controller;
    }

    @Bean
    public FixCalMessageDispatcher messageDispatcher() {
        FixCalMessageDispatcher dispatcher = new FixCalMessageDispatcher();
        dispatcher.setHost(classicConfig.experimentHost);
        dispatcher.setDbUtil(baseConfig.dbUtil());
        return dispatcher;
    }

    @Bean
    public ExperimentConsole experimentConsole () {
        ExperimentConsole console = new ExperimentConsole();

        console.setPaused(classicConfig.xperExperimentInitialPause());
        console.setConsoleRenderer(classicConfig.consoleRenderer());
        console.setMonkeyScreenDimension(classicConfig.monkeyWindow().getScreenDimension());
        console.setModel(classicConfig.experimentConsoleModel());
        console.setCanvasScaleFactor(3);

        ExperimentMessageReceiver receiver = classicConfig.messageReceiver();
        // register itself to avoid circular reference
        receiver.addMessageReceiverEventListener(console);

        List<IConsolePlugin> plugins = new LinkedList<>();
        plugins.add(fixTrainConsolePlugin());
        console.setConsolePlugins(plugins);
        return console;
    }

    @Bean
    public FixTrainConsolePlugin fixTrainConsolePlugin(){
        FixTrainConsolePlugin plugin = new FixTrainConsolePlugin();
        plugin.setClient(fixTrainClient());
        plugin.setFixTrainObjectMap(fixTrainObjectMap());
        return plugin;
    }

    @Bean
    public FixTrainClient fixTrainClient(){
        FixTrainClient client = new FixTrainClient();
        client.setHost(classicConfig.experimentHost);
        return client;
    }

    @Bean
    public NullTaskDoneCache taskDoneCache() {
        return new NullTaskDoneCache();
    }


    @Bean(scope = DefaultScopes.PROTOTYPE)
    public Boolean xperFixationOnWithStimuli() {
        return true;
    }

    @Bean
    public Boolean xperDoEmptyTask() {
        return true;
    }

    @Bean
    public Boolean xperRightIscanEyeZeroUpdateEnabled () {
        return false;
    }

    @Bean
    public Boolean xperLeftIscanEyeZeroUpdateEnabled () {
        return false;
    }

}