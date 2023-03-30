package org.xper.allen.config;

import org.apache.commons.math.analysis.UnivariateRealFunction;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.ga.regimescore.*;
import org.xper.allen.ga.regimescore.ParentChildBinThresholdsScoreSource.NormalizedResponseBin;
import org.xper.allen.ga.regimescore.RegimeScoreSource.RegimeTransition;
import org.xper.allen.ga3d.blockgen.LinearSpline;
import org.xper.allen.newga.blockgen.NewGABlockGenerator;
import org.xper.allen.util.MultiGaDbUtil;
import org.xper.config.BaseConfig;
import org.xper.experiment.DatabaseTaskDataSource;

import javax.vecmath.Point2d;
import java.util.*;

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

    @Bean
    public SlotSelectionProcess slotSelectionProcess() {
        SlotSelectionProcess slotSelectionProcess = new SlotSelectionProcess();
        slotSelectionProcess.setDbUtil(dbUtil());
        slotSelectionProcess.setNumChildrenToSelect(numberOfStimuliPerGeneration);
        slotSelectionProcess.setSpikeRateSource(spikeRateSource());
        slotSelectionProcess.setRegimeScoreSource(regimeScoreSource());
        slotSelectionProcess.setSlotFunctionForLineage(slotFunctionForLineage());
        slotSelectionProcess.setSlotFunctionForRegimes(slotFunctionForRegimes());
        slotSelectionProcess.setFitnessFunctionForRegimes(fitnessFunctionForRegimes());
        return slotSelectionProcess;
    }

    private UnivariateRealFunction slotFunctionForLineage() {

        List<Point2d> controlPoints = new ArrayList<>();
        controlPoints.add(new Point2d(0, 0));
        controlPoints.add(new Point2d(1, 1.0/3.0));
        controlPoints.add(new Point2d(2, 2.0/3.0));
        controlPoints.add(new Point2d(3.9, 1));
        controlPoints.add(new Point2d(4, 0));
        return new LinearSpline(controlPoints);
    }

    @Bean
    public RegimeScoreSource regimeScoreSource() {
        RegimeScoreSource regimeScoreSource = new RegimeScoreSource();
        regimeScoreSource.setDbUtil(dbUtil());
        regimeScoreSource.setLineageScoreSourceForRegimeTransitions(lineageScoreSourceForRegimeTransitions());
        return regimeScoreSource;
    }

    @Bean
    public Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions() {
        Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions = new HashMap<>();
        lineageScoreSourceForRegimeTransitions.put(RegimeTransition.ZERO_TO_ONE, regimeZeroToOne());
        lineageScoreSourceForRegimeTransitions.put(RegimeTransition.ONE_TO_TWO, regimeOneToTwo());
        lineageScoreSourceForRegimeTransitions.put(RegimeTransition.TWO_TO_THREE, regimeTwoToThree());
        lineageScoreSourceForRegimeTransitions.put(RegimeTransition.THREE_TO_FOUR, regimeThreeToFour());
        return lineageScoreSourceForRegimeTransitions;
    }

    @Bean
    public LineageScoreSource regimeZeroToOne() {
        MaxValueLineageScore zeroToOne = new MaxValueLineageScore();
        zeroToOne.setDbUtil(dbUtil());
        zeroToOne.setSpikeRateSource(spikeRateSource());
        zeroToOne.setMaxThresholdSource(regimeZeroToOneThreshold());
        return zeroToOne;
    }

    @Bean
    public ThresholdSource regimeZeroToOneThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 30.0;
            }
        };
    }

    @Bean
    public LineageScoreSource regimeOneToTwo() {
        StabilityOfMaxScoreSource oneToTwo = new StabilityOfMaxScoreSource();
        oneToTwo.setDbUtil(dbUtil());
        oneToTwo.setSpikeRateSource(spikeRateSource());
        oneToTwo.setMaxResponseSource(maxResponseSource());
        oneToTwo.setNormalizedRangeThresholdSource(regimeOneToTwoThreshold());
        return oneToTwo;
    }

    @Bean
    public ThresholdSource regimeOneToTwoThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 10.0;
            }
        };
    }

    @Bean
    public LineageScoreSource regimeTwoToThree() {
        ParentChildThresholdScoreSource twoToThree = new ParentChildThresholdScoreSource();
        twoToThree.setStimType(NewGABlockGenerator.stimTypeForRegime.get(NewGABlockGenerator.Regime.TWO));
        twoToThree.setDbUtil(dbUtil());
        twoToThree.setNumPairThresholdSource(regimeTwoToThreePairThreshold());
        twoToThree.setParentResponseThresholdSource(regimeTwoToThreeParentThreshold());
        twoToThree.setChildResponseThresholdSource(regimeTwoToThreeChildThreshold());
        twoToThree.setSpikeRateSource(spikeRateSource());
        return twoToThree;
    }

    @Bean
    public ThresholdSource regimeTwoToThreePairThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 10.0;
            }
        };
    }

    @Bean
    public ThresholdSource regimeTwoToThreeParentThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 60.0;
            }
        };
    }

    @Bean
    public ThresholdSource regimeTwoToThreeChildThreshold() {
        return regimeTwoToThreeParentThreshold();
    }

    @Bean
    public LineageScoreSource regimeThreeToFour() {
        ParentChildBinThresholdsScoreSource threeToFour = new ParentChildBinThresholdsScoreSource();
        threeToFour.setStimType(NewGABlockGenerator.stimTypeForRegime.get(NewGABlockGenerator.Regime.THREE));
        threeToFour.setDbUtil(dbUtil());
        threeToFour.setParentResponseThresholdSource(regimeThreeToFourParentThreshold());
        threeToFour.setNumPairThresholdSourcesForBins(regimeThreeToFourPairThresholds());
        threeToFour.setSpikeRateSource(spikeRateSource());
        threeToFour.setMaxResponseSource(maxResponseSource());
        return threeToFour;
    }

    @Bean
    public ThresholdSource regimeThreeToFourParentThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 60.0;
            }
        };
    }

    @Bean
    public Map<NormalizedResponseBin, ThresholdSource> regimeThreeToFourPairThresholds() {
        Map<NormalizedResponseBin, ThresholdSource> pairThresholds = new HashMap<>();
        pairThresholds.put(new NormalizedResponseBin(0.0, 0.33), thresholdForRegimeThreeToFourPair());
        pairThresholds.put(new NormalizedResponseBin(0.33, 0.66), thresholdForRegimeThreeToFourPair());
        pairThresholds.put(new NormalizedResponseBin(0.66, 1.0), thresholdForRegimeThreeToFourPair());
        return null;
    }

    @Bean
    public ThresholdSource thresholdForRegimeThreeToFourPair() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 10.0;
            }
        };
    }

    @Bean
    public MaxResponseSource maxResponseSource() {
        MaxResponseSource maxResponseSource = new MaxResponseSource();
        maxResponseSource.setDbUtil(dbUtil());
        maxResponseSource.setMinimumMaxResponse(30.0);
        maxResponseSource.setSpikeRateSource(spikeRateSource());
        return maxResponseSource;
    }

    @Bean
    public SpikeRateSource spikeRateSource() {
        IntanAverageSpikeRateSource spikeRateSource = new IntanAverageSpikeRateSource();
        spikeRateSource.setSpikeDatDirectory(spikeDatPath);
        spikeRateSource.setChannels(channels());
        return spikeRateSource;
    }

    @Bean
    public List<String> channels() {
        return new LinkedList<>();
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