package org.xper.allen.config;

import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.nafc.experiment.juice.LinearControlPointFunction;
import org.xper.allen.pga.FromDbGABlockGenerator;
import org.xper.allen.pga.ReceptiveFieldSource;
import org.xper.allen.pga.StreakJuiceController;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.classic.TrialEventListener;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;
import org.xper.config.IntanRHDConfig;
import org.xper.experiment.DatabaseTaskDataSource;
import org.xper.allen.intan.GAInfoFileNamingStrategy;

import java.util.*;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({MStickPngConfig.class})
public class PGAConfig {
    @Autowired MStickPngConfig mStickPngConfig;
    @Autowired
    ClassicConfig classicConfig;
    @Autowired BaseConfig baseConfig;
    @Autowired
    IntanRHDConfig intanConfig;

    @ExternalValue("number_of_repetitions_per_stimulus")
    public Integer numberOfRepetitionsPerStimulus;


    @Bean
    public FromDbGABlockGenerator generator(){
        FromDbGABlockGenerator generator = new FromDbGABlockGenerator();
        generator.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
        generator.setImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
        generator.setPngMaker(mStickPngConfig.pngMaker());
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setDbUtil(dbUtil());
        generator.setNumTrialsPerStimulus(numberOfRepetitionsPerStimulus);
        generator.setGaName(gaName());
        generator.setRfSource(rfSource());
        generator.setNumCatchTrials(5);
        return generator;
    }

    @Bean
    public String gaName() {
        return "New3D";
    }

    @Bean
    public ReceptiveFieldSource rfSource(){
        ReceptiveFieldSource rfSource = new ReceptiveFieldSource();
        rfSource.setDataSource(baseConfig.dataSource());
        rfSource.setRenderer(classicConfig.experimentGLRenderer());
        return rfSource;
    }

    @Bean
    public MultiGATaskDataSource taskDataSource(){
        return databaseTaskDataSource();
    }

    @Bean
    public MultiGATaskDataSource databaseTaskDataSource() {
        MultiGATaskDataSource source = new MultiGATaskDataSource();
        source.setDbUtil(dbUtil());
        source.setQueryInterval(1000);
        source.setUngetPolicy(DatabaseTaskDataSource.UngetPolicy.TAIL);
        source.setGaNames(Collections.singletonList(generator().getGaName()));
        return source;
    }

    @Bean
    public MultiGaDbUtil dbUtil(){
        MultiGaDbUtil dbUtil = new MultiGaDbUtil();
        dbUtil.setDataSource(baseConfig.dataSource());
        return dbUtil;
    }

    @Bean
    public GAInfoFileNamingStrategy intanFileNamingStrategy(){
        GAInfoFileNamingStrategy strategy = new GAInfoFileNamingStrategy();
        strategy.setBaseNetworkPath(intanConfig.intanRemoteDirectory);
        strategy.setIntan(intanConfig.intan());
        strategy.setGaName(gaName());
        strategy.setDbUtil(dbUtil());
        return strategy;
    }

    @Bean
    public TrialEventListener juiceController(){
        StreakJuiceController controller = new StreakJuiceController();
        controller.setJuice(classicConfig.xperDynamicJuice());
        controller.setStreakRewardFunction(xperStreakRewardFunction());
        return controller;
    }

    @Bean
    public UnivariateRealFunction xperStreakRewardFunction() {
        LinearControlPointFunction f = new LinearControlPointFunction();
        f.setxValues(Arrays.asList(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 100.0)); //streak amounts
        f.setyValues(Arrays.asList(1.0, 1.5, 2.0, 3.0, 4.5, 4.5, 4.5)); //reward amounts
        return f;
    }

}