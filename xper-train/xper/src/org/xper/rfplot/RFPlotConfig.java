package org.xper.rfplot;

import java.util.*;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.classic.TrialDrawingController;
import org.xper.classic.TrialEventListener;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.IntanRHDConfig;
import org.xper.console.ExperimentConsole;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.console.IConsolePlugin;
import org.xper.drawing.TaskScene;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.experiment.TaskDoneCache;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.experiment.listener.RFPlotTaskDataSourceController;
import org.xper.experiment.mock.NullTaskDoneCache;
import org.xper.rfplot.drawing.RFPlotBlankObject;
import org.xper.rfplot.drawing.RFPlotDrawable;
import org.xper.rfplot.drawing.RFPlotGaborObject;
import org.xper.rfplot.drawing.RFPlotImgObject;
import org.xper.rfplot.gui.*;
import org.xper.rfplot.gui.scroller.*;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class RFPlotConfig {
	@Autowired AcqConfig acqConfig;
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired
	IntanRHDConfig intanConfig;

	@ExternalValue("rfplot.png_library_path_generator")
	public String pngLibraryPath_generator;

	@ExternalValue("rfplot.png_library_path_experiment")
	public String pngLibraryPath_experiment;

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
		scene.setRfObjectMap(namesForDrawables());
		scene.setRenderer(rfRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setBlankScreen(new BlankScreen());
		scene.setMarker(classicConfig.screenMarker());
		return scene;
	}

	@Bean
	public Map<String, RFPlotDrawable> namesForDrawables() {
		LinkedHashMap<String, RFPlotDrawable> refObjMap = new LinkedHashMap<String, RFPlotDrawable>();
		refObjMap.put(RFPlotBlankObject.class.getName(), new RFPlotBlankObject());
		refObjMap.put(RFPlotGaborObject.class.getName(), new RFPlotGaborObject());
		refObjMap.put(RFPlotImgObject.class.getName(), new RFPlotImgObject(imgPathScroller().getFirstPath()));
		return refObjMap;
	}

	@Bean
	public Map<String, RFPlotStimModulator> modulatorsForDrawables(){
		LinkedHashMap<String, RFPlotStimModulator> refModulatorMap = new LinkedHashMap<>();
		refModulatorMap.put(RFPlotGaborObject.class.getName(), gaborModulator());
		refModulatorMap.put(RFPlotImgObject.class.getName(), imgModulator());
		return refModulatorMap;
	}

	@Bean
	public RFPlotStimModulator gaborModulator() {
		RFPlotStimModulator gaborModulator = new RFPlotStimModulator(gaborModeScrollerMap());
		return gaborModulator;
	}

	@Bean
	public LinkedHashMap<String, RFPlotScroller> gaborModeScrollerMap(){
		LinkedHashMap<String, RFPlotScroller> map = new LinkedHashMap<>();
		map.put("Size", new SizeScroller());
		map.put("Orientation", new OrientationScroller());
		map.put("Color", new HueScroller());
		return map;
	}

	@Bean
	public RFPlotStimModulator imgModulator(){
		RFPlotStimModulator pngModulator = new RFPlotStimModulator(imgModeScrollerMap());
		return pngModulator;
	}


	@Bean
	public LinkedHashMap<String, RFPlotScroller> imgModeScrollerMap(){
		LinkedHashMap<String, RFPlotScroller> map = new LinkedHashMap<>();
		map.put("Path", imgPathScroller());
		map.put("Size", new SizeScroller());
		map.put("Orientation", new OrientationScroller());
		map.put("Hue", new HueScroller());
		map.put("Saturation", new SaturationScroller());
		map.put("Lightness", new LightnessScroller());
		return map;
	}

	@Bean
	public ImgPathScroller imgPathScroller() {
		ImgPathScroller scroller = new ImgPathScroller();
		scroller.setLibraryPath_generator(pngLibraryPath_generator);
		scroller.setLibraryPath_experiment(pngLibraryPath_experiment);
		scroller.init();
		return scroller;
	}

	@Bean
	public RFPlotConsolePlugin rfPlotConsolePlugin(){
		RFPlotConsolePlugin plugin = new RFPlotConsolePlugin();
		plugin.setClient(rfPlotClient());
		plugin.setNamesForDrawables(namesForDrawables());
		plugin.setModulatorsForDrawables(modulatorsForDrawables());
		plugin.setConsoleRenderer(classicConfig.consoleRenderer());
		plugin.setPlotter(rfPlotter());
		plugin.setDbUtil(baseConfig.dbUtil());
		plugin.setTimeUtil(baseConfig.localTimeUtil());
		return plugin;
	}
	@Bean
	public RFPlotDrawer rfPlotter(){
		RFPlotDrawer plotter = new RFPlotDrawer();
		return plotter;
	}

	@Bean
	public RFPlotClient rfPlotClient(){
		return new RFPlotTaskDataSourceClient(classicConfig.experimentHost);
	}

	@Bean
	public RFPlotTaskDataSource taskDataSource() {
		RFPlotTaskDataSource taskDataSource = new RFPlotTaskDataSource();
		taskDataSource.setHost(classicConfig.experimentHost);
		taskDataSource.setRefObjMap(namesForDrawables());
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
		listeners.add(intanConfig.intanController());
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


}