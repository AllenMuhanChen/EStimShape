package org.xper.config;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.exception.DbException;
import org.xper.intan.*;
import org.xper.util.DbUtil;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(ClassicConfig.class)
public class TestConfig {

    @Autowired
    BaseConfig baseConfig;

    @ExternalValue("test.jdbc.driver")
    public String jdbcDriver;

    @ExternalValue("test.jdbc.url")
    public String jdbcUrl;

    @ExternalValue("test.jdbc.username")
    public String jdbcUserName;

    @ExternalValue("test.jdbc.password")
    public String jdbcPassword;

    @ExternalValue("test.intan.host")
    public String intanHost;

    @ExternalValue("test.intan.port.command")
    public String intanCommandPort;

    @ExternalValue("test.intan.default_save_path")
    public String intanDefaultSavePath;

    @ExternalValue("test.intan.default_base_filename")
    public String intanDefaultBaseFilename;

    @Bean
    public DbUtil dbUtil() {
        DbUtil util = new DbUtil();
        util.setDataSource(dataSource());
        return util;
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

    @Bean
    public IntanFileNamingStrategy intanFileNamingStrategy(){
        TaskIdFileNamingStrategy strategy = new TaskIdFileNamingStrategy();
        strategy.setIntanController(intanController());
        return strategy;
    }

}
