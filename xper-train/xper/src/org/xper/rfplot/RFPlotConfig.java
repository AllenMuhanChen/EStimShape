package org.xper.rfplot;

import java.util.HashMap;
import java.util.LinkedHashMap;
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
import org.xper.classic.MarkEveryStepTrialDrawingController;
import org.xper.classic.MarkStimTrialDrawingController;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.Context;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.experiment.TaskDoneCache;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.experiment.listener.RFPlotTaskDataSourceController;
import org.xper.experiment.mock.NullTaskDoneCache;
import org.xper.rfplot.gui.RFPlotConsolePlugin;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class RFPlotConfig {
	@Autowired AcqConfig acqConfig;
	@Autowired ClassicConfig classicConfig;
	
	@Bean
	public PerspectiveRenderer rfRenderer () {
		PerspectiveRenderer renderer = new PerspectiveRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		return renderer;
	}


	@Bean
	public TaskScene taskScene() {
		RFPlotScene scene = new RFPlotScene();
		scene.setRfObjectMap(refObjMap());
		scene.setRenderer(rfRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setBlankScreen(new BlankScreen());
		scene.setMarker(classicConfig.screenMarker());
		return scene;
	}

	@Bean
	public LinkedHashMap<String, RFPlotDrawable> refObjMap() {
		LinkedHashMap<String, RFPlotDrawable> refObjMap = new LinkedHashMap<String, RFPlotDrawable>();
		refObjMap.put(RFPlotGaborObject.class.getName(), new RFPlotGaborObject());
		refObjMap.put(RFPlotBlankObject.class.getName(), new RFPlotBlankObject());

		return refObjMap;
	}

	@Bean
	public RFPlotTaskDataSource taskDataSource() {
		RFPlotTaskDataSource taskDataSource = new RFPlotTaskDataSource();
		taskDataSource.setHost(classicConfig.experimentHost);
		return taskDataSource;
	}
	
	@Bean
	public TaskDoneCache taskDoneCache () {
		NullTaskDoneCache cache = new NullTaskDoneCache();
		return cache;
	}
	
	@Bean 
	public RFPlotTaskDataSourceController taskDataSourceController () {
		RFPlotTaskDataSourceController controller = new RFPlotTaskDataSourceController();
		controller.setTaskDataSource(taskDataSource());
		return controller;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<ExperimentEventListener> experimentEventListeners () {
		List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
		listeners.add(classicConfig.messageDispatcher());
		listeners.add(taskDataSourceController());
		listeners.add(classicConfig.messageDispatcherController());
		listeners.add(classicConfig.eyeZeroLogger());
		listeners.add(classicConfig.experimentCpuBinder());
		return listeners;
	}
	
	@Bean (scope = DefaultScopes.PROTOTYPE)
	public List<TrialEventListener> trialEventListeners () {
		List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
		trialEventListener.add(classicConfig.eyeMonitorController());
		trialEventListener.add(classicConfig.trialEventLogger());
		trialEventListener.add(classicConfig.experimentProfiler());
		trialEventListener.add(classicConfig.messageDispatcher());
		trialEventListener.add(classicConfig.juiceController());
		trialEventListener.add(classicConfig.trialSyncController());
		trialEventListener.add(classicConfig.jvmManager());
		if (!acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NONE)) {
			trialEventListener.add(classicConfig.dynamicJuiceUpdater());
		}
		return trialEventListener;
	}

	@Bean
	public TrialDrawingController drawingController() {
		RFPlotMarkStimTrialDrawingController controller;
//		if (classicConfig.markEveryStep) {
//			controller = new MarkEveryStepTrialDrawingController();
//		} else {
//			controller = new RFPlotMarkStimTrialDrawingController();
//		}
		controller = new RFPlotMarkStimTrialDrawingController();
		controller.setWindow(classicConfig.monkeyWindow());
		controller.setTaskScene(taskScene());
		controller.setFixationOnWithStimuli(classicConfig.xperFixationOnWithStimuli());
		return controller;
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
		plugins.add(rfPlotConsolePlugin());
		console.setConsolePlugins(plugins);
		return console;
	}

	@Bean
	public RFPlotConsolePlugin rfPlotConsolePlugin(){
		RFPlotConsolePlugin plugin = new RFPlotConsolePlugin();
		plugin.setClient(rfPlotClient());
		plugin.setRfObjectMap(refObjMap());
		plugin.setConsoleRenderer(classicConfig.consoleRenderer());
		return plugin;
	}

	@Bean
	public RFPlotClient rfPlotClient(){
		return new RFPlotTaskDataSourceClient(classicConfig.experimentHost);
	}
}