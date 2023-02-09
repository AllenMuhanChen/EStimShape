package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.ga3d.blockgen.GA3DBlockGen;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.config.BaseConfig;
import org.xper.experiment.DatabaseTaskDataSource;

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
    public GA3DBlockGen generator(){
        GA3DBlockGen generator = new GA3DBlockGen();
        generator.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
        generator.setMaxImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
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
        source.setUngetPolicy(DatabaseTaskDataSource.UngetPolicy.HEAD);
        source.setGaNames(generator().getGaNames());
        return source;
    }


    @Bean
    public ParentSelector parentSelector(){
        IntanSpikeParentSelector parentSelector = new IntanSpikeParentSelector();
        parentSelector.setDbUtil(dbUtil());
        parentSelector.setSpikeDatDirectory(spikeDatPath);
        parentSelector.setSpikeRateAnalyzer(spikeRateAnalyzer());
        return parentSelector;
    }

    @Bean
    public SpikeRateAnalyzer spikeRateAnalyzer(){
        StandardSpikeRateAnalyzer spikeRateAnalyzer = new StandardSpikeRateAnalyzer();
        return spikeRateAnalyzer;
    }



}
