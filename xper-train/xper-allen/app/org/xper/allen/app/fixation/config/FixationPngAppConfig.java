package org.xper.allen.app.fixation.config;

import java.util.HashMap;

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
import org.xper.allen.app.fixation.FixationPngBlockGen;
import org.xper.allen.app.fixation.PngScene;
import org.xper.allen.fixcal.RewardButtonExperimentConsole;
import org.xper.allen.fixcal.RewardButtonExperimentConsoleModel;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunner;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunnerClient;
import org.xper.allen.nafc.eye.FreeHeadNAFCEyeMonitorController;
import org.xper.allen.nafc.eye.LaggingMovingAverageEyeZeroAlgorithm;
import org.xper.allen.util.AllenDbUtil;
import org.xper.classic.vo.SlideTrialExperimentState;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.object.BlankScreen;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveStereoRenderer;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.zero.MovingAverageEyeZeroAlgorithm;

@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class FixationPngAppConfig {
	@Autowired ClassicConfig classicConfig;
	@Autowired BaseConfig baseConfig;
	@Autowired AcqConfig acqConfig;
	
	@ExternalValue("generator.png_path")
	public String generatorPngPath;

	@ExternalValue("experiment.png_path")
	public String experimentPngPath;
	
	@Bean
	public PngScene taskScene() {
		PngScene scene = new PngScene();
		scene.setRenderer(experimentGLRenderer());
		scene.setFixation(classicConfig.experimentFixationPoint());
		scene.setMarker(classicConfig.screenMarker());
		scene.setBlankScreen(new BlankScreen());
		scene.setScreenHeight(classicConfig.xperMonkeyScreenHeight());
		scene.setScreenWidth(classicConfig.xperMonkeyScreenWidth());
		scene.setDistance(classicConfig.xperMonkeyScreenDistance());
		scene.setBackgroundColor(xperBackgroundColor());
		return scene;
	}
	
	/**
	 * Use PerspectiveStereoRenderer for mono and stereo, only changing the xper screen width accordingly. 
	 * @return
	 */
	@Bean
	public AbstractRenderer experimentGLRenderer () {
		PerspectiveStereoRenderer renderer = new PerspectiveStereoRenderer();
		renderer.setDistance(classicConfig.xperMonkeyScreenDistance());
		renderer.setDepth(classicConfig.xperMonkeyScreenDepth());
		renderer.setHeight(classicConfig.xperMonkeyScreenHeight());
		renderer.setWidth(classicConfig.xperMonkeyScreenWidth());
		renderer.setPupilDistance(classicConfig.xperMonkeyPupilDistance());
		renderer.setInverted(classicConfig.xperMonkeyScreenInverted());
		return renderer;
	}
	
	@Bean
	public FixationPngBlockGen generator() {
		FixationPngBlockGen gen = new FixationPngBlockGen();
		gen.setDbUtil(allenDbUtil());
		gen.setGlobalTimeUtil(acqConfig.timeClient());
		gen.setGeneratorPngPath(generatorPngPath);
		gen.setExperimentPngPath(experimentPngPath);
		return gen;
	}
	
	/**
	 * It's fine to use this for Fixation rather than NAFC, since we still want the eye-zero update
	 * to happen right after fixation. 
	 * @return
	 */
	@Bean
	public FreeHeadNAFCEyeMonitorController eyeMonitorController() {
		FreeHeadNAFCEyeMonitorController controller = new FreeHeadNAFCEyeMonitorController();
		controller.setEyeSampler(classicConfig.eyeSampler());
		controller.setEyeWindowAdjustable(classicConfig.eyeWindowAdjustables());
		controller.setEyeDeviceWithAdjustableZero(classicConfig.eyeZeroAdjustables());
		return controller;
	}
	
	@Bean
	public AllenDbUtil allenDbUtil() {
		AllenDbUtil dbUtil = new AllenDbUtil();
		dbUtil.setDataSource(baseConfig.dataSource());
		return dbUtil;
	}
	
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public double[] xperBackgroundColor() {
		return new double[]{Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 0)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 1)),
				Double.parseDouble(baseConfig.systemVariableContainer().get("xper_background_color", 2))};
	}
	
	@Bean
	public RewardButtonExperimentConsole experimentConsole () {
		RewardButtonExperimentConsole console = new RewardButtonExperimentConsole();
		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(classicConfig.consoleRenderer());
		console.setMonkeyScreenDimension(classicConfig.monkeyWindow().getScreenDimension());
		console.setModel(experimentConsoleModel());
		console.setCanvasScaleFactor(3);
		
		ExperimentMessageReceiver receiver = classicConfig.messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	
	
	@Bean
	public RewardButtonExperimentConsoleModel experimentConsoleModel () {
		RewardButtonExperimentConsoleModel model = new RewardButtonExperimentConsoleModel();
		model.setMessageReceiver(classicConfig.messageReceiver());
		model.setLocalTimeUtil(baseConfig.localTimeUtil());
		
		HashMap<String, MappingAlgorithm> eyeMappingAlgorithm = new HashMap<String, MappingAlgorithm>();
		eyeMappingAlgorithm.put(classicConfig.xperLeftIscanId(), classicConfig.leftIscanMappingAlgorithm());
		eyeMappingAlgorithm.put(classicConfig.xperRightIscanId(), classicConfig.rightIscanMappingAlgorithm());
		model.setEyeMappingAlgorithm(eyeMappingAlgorithm);
		
		model.setExperimentRunnerClient(experimentRunnerClient());
		model.setChannelMap(classicConfig.iscanChannelMap());
		model.setMessageHandler(classicConfig.messageHandler());
		
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
	public RewardButtonExperimentRunner experimentRunner () {
		RewardButtonExperimentRunner runner = new RewardButtonExperimentRunner();
		runner.setHost(classicConfig.experimentHost);
		runner.setExperiment(classicConfig.experiment());
		runner.setJuice(classicConfig.xperDynamicJuice());
		runner.setDbUtil(allenDbUtil());
		runner.setTimeUtil(baseConfig.localTimeUtil());
		return runner;
	}
	
	@Bean
	public RewardButtonExperimentRunnerClient experimentRunnerClient() {
		RewardButtonExperimentRunnerClient client = new RewardButtonExperimentRunnerClient(classicConfig.experimentHost);
		return client;
	}
	
	@Bean(scope = DefaultScopes.PROTOTYPE)
	public LaggingMovingAverageEyeZeroAlgorithm leftIscanMovingAverageEyeZeroAlgorithm() {
		LaggingMovingAverageEyeZeroAlgorithm algo = new LaggingMovingAverageEyeZeroAlgorithm(classicConfig.xperLeftIscanEyeZeroAlgorithmSpan());
		algo.setEyeZeroUpdateEyeWinThreshold(classicConfig.xperLeftIscanEyeZeroAlgorithmEyeWindowThreshold());
		algo.setEyeZeroUpdateMinSample(classicConfig.xperLeftIscanEyeZeroAlgorithmMinSample());
		algo.setEyeZeroUpdateEyeWinCenter(classicConfig.xperEyeWindowCenter());
		return algo;
	}

	@Bean(scope = DefaultScopes.PROTOTYPE)
	public LaggingMovingAverageEyeZeroAlgorithm rightIscanMovingAverageEyeZeroAlgorithm() {
		LaggingMovingAverageEyeZeroAlgorithm algo = new LaggingMovingAverageEyeZeroAlgorithm(classicConfig.xperRightIscanEyeZeroAlgorithmSpan());
		algo.setEyeZeroUpdateEyeWinThreshold(classicConfig.xperRightIscanEyeZeroAlgorithmEyeWindowThreshold());
		algo.setEyeZeroUpdateMinSample(classicConfig.xperRightIscanEyeZeroAlgorithmMinSample());
		algo.setEyeZeroUpdateEyeWinCenter(classicConfig.xperEyeWindowCenter());
		return algo;
	}

}
