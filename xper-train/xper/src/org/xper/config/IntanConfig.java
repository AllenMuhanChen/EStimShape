package org.xper.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.intan.IntanClient;
import org.xper.intan.IntanController;
import org.xper.intan.IntanMessageDispatcher;

import java.util.LinkedList;
import java.util.List;

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
        intanMessageDispatcher.setIntanController(intanController());
        return intanMessageDispatcher;
    }

    @Bean
    public IntanController intanController() {
        IntanController intanController = new IntanController();
        intanController.setIntanClient(intanClient());
        intanController.setDefaultSavePath(intanDefaultSavePath);
        intanController.setDefaultBaseFileName(intanDefaultBaseFilename);
        return intanController;
    }

    @Bean
    public IntanClient intanClient(){
        IntanClient intanClient = new IntanClient();
        intanClient.setHost(intanHost);
        intanClient.setPort(Integer.parseInt(intanCommandPort));
        intanClient.setTimeUtil(baseConfig.localTimeUtil());
        return intanClient;
    }


}
