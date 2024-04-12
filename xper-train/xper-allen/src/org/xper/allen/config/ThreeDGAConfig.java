package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.ga3d.blockgen.GA3DLineageBlockGenerator;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.config.BaseConfig;
import org.xper.experiment.DatabaseTaskDataSource;

import java.util.LinkedList;
import java.util.List;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({MStickPngConfig.class})
public class ThreeDGAConfig {
    @Autowired MStickPngConfig mStickPngConfig;
    @Autowired BaseConfig baseConfig;

    @ExternalValue("generator.spike_dat_path")
    public String spikeDatPath;

    @ExternalValue("number_of_lineages")
    public String numberLineages;

    @Bean
    public GA3DLineageBlockGenerator generator(){
        GA3DLineageBlockGenerator generator = new GA3DLineageBlockGenerator();
        generator.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
        generator.setImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
        generator.setPngMaker(mStickPngConfig.pngMaker());
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setDbUtil(dbUtil());
        generator.setGaBaseName("3D");
        generator.setParentSelector(parentSelector());
        generator.setNumLineages(Integer.parseInt(numberLineages));
        return generator;
    }

    @Bean
    public MultiGaDbUtil dbUtil(){
        MultiGaDbUtil dbUtil = new MultiGaDbUtil();
        dbUtil.setDataSource(baseConfig.dataSource());
        return dbUtil;
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
        source.setGaNames(generator().getGaNames());
        return source;
    }


    @Bean
    public ParentSelector parentSelector(){
        AverageSpikeRateParentSelector parentSelector = new AverageSpikeRateParentSelector();
        parentSelector.setDbUtil(dbUtil());
        parentSelector.setSpikeRateSource(spikeRateSource());
        parentSelector.setParentSelectorStrategy(spikeRateAnalyzer());
        return parentSelector;
    }

    private SpikeRateSource spikeRateSource() {
        IntanAverageSpikeRateSource spikeRateSource = new IntanAverageSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory(spikeDatPath);
        spikeRateSource.setChannels(channels());
        return spikeRateSource;
    }

    //TODO: figure out the best way to get the channels we want to analyze in the GA
    private List<String> channels() {
        return new LinkedList<>();
    }


    @Bean
    public ParentAnalysisStrategy spikeRateAnalyzer(){
        RamParentAnalysisStrategy spikeRateAnalyzer = new RamParentAnalysisStrategy();
        return spikeRateAnalyzer;
    }



}