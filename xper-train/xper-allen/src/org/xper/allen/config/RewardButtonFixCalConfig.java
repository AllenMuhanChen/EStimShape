package org.xper.allen.config;

import java.util.ArrayList;
import java.util.HashMap;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.allen.fixcal.RewardButtonExperimentConsole;
import org.xper.allen.fixcal.RewardButtonExperimentConsoleModel;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunner;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunnerClient;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.FixCalConfig;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.drawing.renderer.AbstractRenderer;
import org.xper.drawing.renderer.PerspectiveRenderer;
import org.xper.experiment.ExperimentRunner;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.eye.strategy.AnyEyeInStategy;
import org.xper.eye.strategy.EyeInStrategy;
/**
 * Uses base fixcal config but:
 * 	Adds button to provide manual reward via the console. Has new experimentConsole class as well as ExperimentRunner. Therefore 
 * the app main methods need to call a different class.
 * @author r2_allen
 *
 */
@Configuration(defaultLazy=Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(FixCalConfig.class)
public class RewardButtonFixCalConfig {
	@Autowired FixCalConfig config;
	@Autowired ClassicConfig classicConfig;
	@Autowired AcqConfig acqConfig;
	@Autowired BaseConfig baseConfig;
	@Bean
	public RewardButtonExperimentConsole experimentConsole () {
		RewardButtonExperimentConsole console = new RewardButtonExperimentConsole();
		
		console.setPaused(classicConfig.xperExperimentInitialPause());
		console.setConsoleRenderer(config.consoleRenderer());
		console.setMonkeyScreenDimension(classicConfig.monkeyWindow().getScreenDimension());
		console.setModel(experimentConsoleModel());
		console.setCanvasScaleFactor(3);
		
		ExperimentMessageReceiver receiver = config.messageReceiver();
		// register itself to avoid circular reference
		receiver.addMessageReceiverEventListener(console);
		
		return console;
	}
	@Bean
	public RewardButtonExperimentConsoleModel experimentConsoleModel () {
		RewardButtonExperimentConsoleModel model = new RewardButtonExperimentConsoleModel();
		model.setMessageReceiver(config.messageReceiver());
		model.setLocalTimeUtil(baseConfig.localTimeUtil());
		
		HashMap<String, MappingAlgorithm> eyeMappingAlgorithm = new HashMap<String, MappingAlgorithm>();
		eyeMappingAlgorithm.put(classicConfig.xperLeftIscanId(), classicConfig.leftIscanMappingAlgorithm());
		eyeMappingAlgorithm.put(classicConfig.xperRightIscanId(), classicConfig.rightIscanMappingAlgorithm());
		model.setEyeMappingAlgorithm(eyeMappingAlgorithm);
		
		model.setExperimentRunnerClient(experimentRunnerClient());
		model.setChannelMap(classicConfig.iscanChannelMap());
		model.setMessageHandler(config.messageHandler());
		
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
		runner.setExperiment(config.experiment());
		runner.setJuice(classicConfig.xperDynamicJuice());
		runner.setDbUtil(baseConfig.dbUtil());
		runner.setTimeUtil(baseConfig.localTimeUtil());
		return runner;
	}
	
	@Bean
	public RewardButtonExperimentRunnerClient experimentRunnerClient() {
		RewardButtonExperimentRunnerClient client = new RewardButtonExperimentRunnerClient(classicConfig.experimentHost);
		return client;
	}
	
	
	
}
