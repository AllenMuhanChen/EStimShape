package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.app.nafc.config.NAFCMStickPngAppConfig;
import org.xper.allen.ga.IntanSpikeParentSelector;
import org.xper.allen.ga.ParentSelector;
import org.xper.allen.ga.SpikeRateAnalyzer;
import org.xper.allen.ga.StandardSpikeRateAnalyzer;
import org.xper.allen.ga3d.blockgen.GA3DBlockGen;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.config.AcqConfig;
import org.xper.config.BaseConfig;
import org.xper.config.ClassicConfig;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({MStickPngConfig.class})
public class ThreeDGAConfig {
    @Autowired MStickPngConfig mStickPngConfig;
    @Autowired BaseConfig baseConfig;

    @ExternalValue("generator.spike_dat_path")
    public String spikeDatPath;

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
        return generator;
    }

    @Bean
    public MultiGaDbUtil dbUtil(){
        MultiGaDbUtil dbUtil = new MultiGaDbUtil();
        dbUtil.setDataSource(baseConfig.dataSource());
        return dbUtil;
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
