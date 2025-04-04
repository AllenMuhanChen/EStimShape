package org.xper.allen.app.twodvsthreed;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.config.MStickPngConfig;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.twodvsthreed.TwoDThreeDLightnessTrialGenerator;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.exception.DbException;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import(MStickPngConfig.class)
public class TwoDVsThreeDConfig {
    @Autowired
    ClassicConfig classicConfig;
    @Autowired
    BaseConfig baseConfig;
    @Autowired
    MStickPngConfig pngConfig;

    @ExternalValue("ga.jdbc.url")
    public String gaJdbcUrl;

    @ExternalValue("ga.spec_path")
    public String gaSpecPath;


    @Bean
    public TwoDThreeDLightnessTrialGenerator generator(){
        TwoDThreeDLightnessTrialGenerator generator = new TwoDThreeDLightnessTrialGenerator();
        generator.setGaDataSource(gaDataSource());
        generator.setGaSpecPath(gaSpecPath);
        generator.setRfSource(rfSource());
        generator.setDbUtil(baseConfig.dbUtil());
        generator.setExperimentPngPath(pngConfig.experimentPngPath);
        generator.setGeneratorPngPath(pngConfig.generatorPngPath);
        generator.setGeneratorSpecPath(pngConfig.generatorSpecPath);
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setPngMaker(pngConfig.pngMaker());
        generator.setImageDimensionDegrees(pngConfig.xperMaxImageDimensionDegrees());
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