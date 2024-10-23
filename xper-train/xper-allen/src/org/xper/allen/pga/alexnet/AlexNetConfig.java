package org.xper.allen.pga.alexnet;

import com.mchange.v2.c3p0.ComboPooledDataSource;
import org.springframework.config.java.annotation.Bean;
import org.springframework.config.java.annotation.Configuration;
import org.springframework.config.java.annotation.ExternalValue;
import org.springframework.config.java.annotation.Lazy;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.alden.drawing.drawables.PNGmaker;
import org.xper.allen.drawing.composition.AllenPNGMaker;
import org.xper.allen.util.DPIUtil;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.exception.DbException;
import org.xper.time.DefaultTimeUtil;
import org.xper.time.TimeUtil;
import org.xper.util.DbUtil;
import org.xper.drawing.RGBColor;

import javax.sql.DataSource;
import java.beans.PropertyVetoException;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
public class AlexNetConfig {
    @ExternalValue("jdbc.driver")
    public String jdbcDriver;

    @ExternalValue("jdbc.url")
    public String jdbcUrl;

    @ExternalValue("jdbc.username")
    public String jdbcUserName;

    @ExternalValue("jdbc.password")
    public String jdbcPassword;

    @ExternalValue("generator.png_path")
    public String generatorPngPath;

    @ExternalValue("experiment.png_path")
    public String experimentPngPath;

    @ExternalValue("generator.spec_path")
    public String generatorSpecPath;

    @ExternalValue("experiment.ga.name")
    public String gaName;

    @Bean
    public FromDbAlexNetGABlockGenerator generator(){
        FromDbAlexNetGABlockGenerator generator = new FromDbAlexNetGABlockGenerator();
        generator.setDbUtil(dbUtil());
        generator.setGlobalTimeUtil(localTimeUtil());
        generator.setGeneratorPngPath(generatorPngPath);
        generator.setExperimentPngPath(experimentPngPath);
        generator.setGeneratorSpecPath(generatorSpecPath);
        generator.setPngMaker(pngMaker());
        generator.setGaName(gaName);
        return generator;
    }

    @Bean
    public TimeUtil localTimeUtil() {
        return new DefaultTimeUtil();
    }

    @Bean
    public MultiGaDbUtil dbUtil() {
        MultiGaDbUtil util = new MultiGaDbUtil();
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
    public AllenPNGMaker pngMaker(){
        AllenPNGMaker pngMaker = new AllenPNGMaker();
        pngMaker.setWidth(227);
        pngMaker.setHeight(227);
        pngMaker.setNoiseMapper(null);
        pngMaker.setDistance(500);
        pngMaker.setDepth(0);
        pngMaker.setPupilDistance(50);
        pngMaker.setBackColor(new RGBColor(0.5,0.5,0.5));
        return pngMaker;
    }

//    @Bean
//    public DPIUtil dpiUtil(){
//        DPIUtil dpiUtil = new DPIUtil();
//        dpiUtil.setRenderer(classicConfig.experimentGLRenderer());
//        dpiUtil.setDpi(xperMonkeyScreenDPI());
//        dpiUtil.setMaxStimulusDimensionDegrees(xperMaxImageDimensionDegrees());
////        dpiUtil.setGeneratorDPI(91.79);
//        dpiUtil.setGeneratorDPI(81.59);
//        return dpiUtil;
//    }



}