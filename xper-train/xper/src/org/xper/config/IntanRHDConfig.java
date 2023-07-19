package org.xper.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.intan.*;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class IntanRHDConfig {

    @Autowired
    BaseConfig baseConfig;

    @ExternalValue("intan.recording.enabled")
    public boolean intanRecordingEnabled;

    @ExternalValue("intan.host")
    public String intanHost;

    @ExternalValue("intan.port.command")
    public String intanCommandPort;

    @ExternalValue("intan.default_save_path")
    public String intanDefaultSavePath;

    @ExternalValue("intan.default_base_filename")
    public String intanDefaultBaseFilename;

    @ExternalValue("intan.remote_directory")
    public String intanRemoteDirectory;

    @Bean
    public IntanRecordingController intanController(){
        IntanRecordingController intanController = new IntanRecordingController();
        intanController.setIntan(intan());
        intanController.setRecordingEnabled(intanRecordingEnabled);
        intanController.setFileNamingStrategy(intanFileNamingStrategy());
        return intanController;
    }

    @Bean
    public IntanRHD intan() {
        IntanRHD intanRHD = new IntanRHD();
        intanRHD.setIntanClient(intanClient());
        intanRHD.setDefaultSavePath(intanDefaultSavePath);
        intanRHD.setDefaultBaseFileName(intanDefaultBaseFilename);
        return intanRHD;
    }

    @Bean
    public IntanClient intanClient(){
        IntanClient intanClient = new IntanClient();
        intanClient.setHost(intanHost);
        intanClient.setPort(Integer.parseInt(intanCommandPort));
        intanClient.setTimeUtil(baseConfig.localTimeUtil());
        return intanClient;
    }

    @Bean
    public IntanFileNamingStrategy<Long> intanFileNamingStrategy(){
        TaskIdFileNamingStrategy strategy = new TaskIdFileNamingStrategy();
        strategy.setBaseNetworkPath(intanRemoteDirectory);
        strategy.setIntan(intan());
        return strategy;
    }


}