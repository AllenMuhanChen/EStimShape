package org.xper.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.intan.*;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class IntanConfig {

    @Autowired
    BaseConfig baseConfig;

    @ExternalValue("intan.host")
    public String intanHost;

    @ExternalValue("intan.port.command")
    public String intanCommandPort;

    @ExternalValue("intan.default_save_path")
    public String intanDefaultSavePath;

    @ExternalValue("intan.default_base_filename")
    public String intanDefaultBaseFilename;

    @Bean
    public IntanMessageDispatcher intanMessageDispatcher(){
        IntanMessageDispatcher intanMessageDispatcher = new IntanMessageDispatcher();
        intanMessageDispatcher.setFileNamingStrategy(intanFileNamingStrategy());
        intanMessageDispatcher.setIntanController(intanController());
        return intanMessageDispatcher;
    }

    @Bean
    public IntanRecordingController intanController() {
        IntanRecordingController intanRecordingController = new IntanRecordingController();
        intanRecordingController.setIntanClient(intanClient());
        intanRecordingController.setDefaultSavePath(intanDefaultSavePath);
        intanRecordingController.setDefaultBaseFileName(intanDefaultBaseFilename);
        return intanRecordingController;
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
    public IntanFileNamingStrategy intanFileNamingStrategy(){
        TaskIdFileNamingStrategy strategy = new TaskIdFileNamingStrategy();
        strategy.setIntanController(intanController());
        return strategy;
    }


}