package org.xper.allen.app.twodvsthreed;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.fixation.config.FixationPngAppConfig;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.twodvsthreed.TwoDVsThreeDTrialGenerator;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.exception.DbException;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(FixationPngAppConfig.class)
public class TwoDVsThreeDConfig {
    @Autowired
    ClassicConfig classicConfig;

    @Autowired
    BaseConfig baseConfig;

    @ExternalValue("ga.jdbc.url")
    public String gaJdbcUrl;

    @ExternalValue("ga.spec_path")
    public String gaSpecPath;

    @Bean
    TwoDVsThreeDTrialGenerator generator(){
        TwoDVsThreeDTrialGenerator generator = new TwoDVsThreeDTrialGenerator();
        generator.setGaDataSource(gaDataSource());
        generator.setGaSpecPath(gaSpecPath);
        generator.setRfSource(rfSource());
        generator.setDbUtil(baseConfig.dbUtil());
        return generator;
    }

    @Bean
    public ReceptiveFieldSource rfSource(){
        ReceptiveFieldSource rfSource = new ReceptiveFieldSource();
        rfSource.setDataSource(gaDataSource());
        rfSource.setRenderer(classicConfig.experimentGLRenderer());
        return rfSource;
    }

    @Bean
    public DataSource gaDataSource(){
        ComboPooledDataSource source = new ComboPooledDataSource();
        try {
            source.setDriverClass(baseConfig.jdbcDriver);
        } catch (PropertyVetoException e) {
            throw new DbException(e);
        }
        source.setJdbcUrl(gaJdbcUrl);
        source.setUser(baseConfig.jdbcUserName);
        source.setPassword(baseConfig.jdbcPassword);
        return source;
    }

}