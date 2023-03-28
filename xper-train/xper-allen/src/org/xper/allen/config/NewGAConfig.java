package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.IntanAverageSpikeRateSource;
import org.xper.allen.ga.MultiGATaskDataSource;
import org.xper.allen.ga.SlotSelectionProcess;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.ga.regimescore.RegimeScoreSource;
import org.xper.allen.newga.blockgen.NewGABlockGenerator;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.config.BaseConfig;
import org.xper.experiment.DatabaseTaskDataSource;

import java.util.Collections;
import java.util.LinkedList;
import java.util.List;

@Configuration(defaultLazy= Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig

@Import({MStickPngConfig.class})
public class NewGAConfig {
    @Autowired MStickPngConfig mStickPngConfig;
    @Autowired BaseConfig baseConfig;

    @ExternalValue("generator.spike_dat_path")
    public String spikeDatPath;

    @ExternalValue("number_of_stimuli_per_generation")
    public Integer numberOfStimuliPerGeneration;

    @Bean
    public NewGABlockGenerator generator(){
        NewGABlockGenerator generator = new NewGABlockGenerator();
        generator.setGeneratorPngPath(mStickPngConfig.generatorPngPath);
        generator.setExperimentPngPath(mStickPngConfig.experimentPngPath);
        generator.setGeneratorSpecPath(mStickPngConfig.generatorSpecPath);
        generator.setMaxImageDimensionDegrees(mStickPngConfig.xperMaxImageDimensionDegrees());
        generator.setPngMaker(mStickPngConfig.pngMaker());
        generator.setGlobalTimeUtil(baseConfig.localTimeUtil());
        generator.setDbUtil(dbUtil());
        generator.setSlotSelectionProcess(slotSelectionProcess());
        return generator;
    }

    private SlotSelectionProcess slotSelectionProcess() {
        SlotSelectionProcess slotSelectionProcess = new SlotSelectionProcess();
        slotSelectionProcess.setDbUtil(dbUtil());
        slotSelectionProcess.setNumChildrenToSelect(numberOfStimuliPerGeneration);
        slotSelectionProcess.setSpikeRateSource(spikeRateSource());
        slotSelectionProcess.setSlotFunctionForLineage(slotFunctionForLineage());
        slotSelectionProcess.setSlotFunctionForRegimes(slotFunctionForRegimes());
        slotSelectionProcess.setFitnessFunctionForRegimes(fitnessFunctionForRegimes());
        slotSelectionProcess.setRegimeScoreSource(regimeScoreSource());
        return slotSelectionProcess;
    }

    private SpikeRateSource spikeRateSource() {
        IntanAverageSpikeRateSource spikeRateSource = new IntanAverageSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory(spikeDatPath);
        spikeRateSource.setChannels(channels());
        return spikeRateSource;
    }

    private List<String> channels() {
        return new LinkedList<>();
    }

    private RegimeScoreSource regimeScoreSource() {
        RegimeScoreSource regimeScoreSource = new RegimeScoreSource();
        regimeScoreSource.setDbUtil(dbUtil());
        regimeScoreSource.setLineageScoreSourceForRegimeTransitions(lineageScoreSourceForRegimeTransitions());
        return regimeScoreSource;
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
        source.setGaNames(Collections.singletonList(generator().getGaBaseName()));
        return source;
    }

    @Bean
    public MultiGaDbUtil dbUtil(){
        MultiGaDbUtil dbUtil = new MultiGaDbUtil();
        dbUtil.setDataSource(baseConfig.dataSource());
        return dbUtil;
    }
}