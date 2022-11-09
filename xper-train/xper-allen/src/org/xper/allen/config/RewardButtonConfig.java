package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.Import;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.acq.mock.SocketSamplingDeviceServer;
import org.xper.allen.fixcal.RewardButtonExperimentConsole;
import org.xper.allen.fixcal.RewardButtonExperimentConsoleModel;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunner;
import org.xper.allen.nafc.experiment.RewardButtonExperimentRunnerClient;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.console.ExperimentMessageReceiver;
import org.xper.exception.ExperimentSetupException;
import org.xper.eye.mapping.MappingAlgorithm;
import org.xper.juice.AnalogJuice;
import org.xper.juice.DynamicJuice;

import java.util.HashMap;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class RewardButtonConfig {
    @Autowired ClassicConfig classicConfig;
    @Autowired BaseConfig baseConfig;
    @Autowired AcqConfig acqConfig;

    @Bean
    public RewardButtonExperimentRunner experimentRunner() {
        RewardButtonExperimentRunner runner = new RewardButtonExperimentRunner();
        runner.setHost(classicConfig.experimentHost);
        runner.setExperiment(classicConfig.experiment());
        runner.setJuice(consoleButtonJuice());
        runner.setDbUtil(baseConfig.dbUtil());
        runner.setTimeUtil(baseConfig.localTimeUtil());
        return runner;
    }

    @Bean
    public RewardButtonExperimentRunnerClient experimentRunnerClient() {
        RewardButtonExperimentRunnerClient client = new RewardButtonExperimentRunnerClient(classicConfig.experimentHost);
        return client;
    }

    @Bean
    public DynamicJuice consoleButtonJuice() {
        AnalogJuice juice = new AnalogJuice();
        juice.setBonusDelay(classicConfig.xperJuiceBonusDelay());
        juice.setBonusProbability(classicConfig.xperJuiceBonusProbability());
        juice.setDelay(classicConfig.xperJuiceDelay());
        juice.setReward(classicConfig.xperJuiceRewardLength());
        juice.setLocalTimeUtil(baseConfig.localTimeUtil());
        if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_NI)) {
            juice.setDevice(classicConfig.niAnalogJuiceDevice());
        } else if (acqConfig.acqDriverName.equalsIgnoreCase(acqConfig.DAQ_COMEDI)) {
            juice.setDevice(classicConfig.comediAnalogJuiceDevice());
        } else {
            throw new ExperimentSetupException("Acq driver " + acqConfig.acqDriverName + " not supported.");
        }
        return juice;
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

}
