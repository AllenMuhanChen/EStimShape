package org.xper.allen.config;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.BeanDefinition;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.xper.allen.ga.*;
import org.xper.allen.ga.regimescore.*;
import org.xper.allen.ga.regimescore.ParentChildBinThresholdsScoreSource.NormalizedResponseBin;
import org.xper.allen.ga.regimescore.RegimeScoreSource.RegimeTransition;
import org.xper.allen.ga3d.blockgen.LinearSpline;
import org.xper.allen.ga3d.blockgen.NaturalSpline;
import org.xper.allen.ga3d.blockgen.Sigmoid;
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

    @ExternalValue("number_of_repetitions_per_stimulus")
    public Integer numberOfRepetitionsPerStimulus;

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
        generator.setNumTrialsPerStimulus(numberOfRepetitionsPerStimulus);
        System.err.println("generator called");
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
        slotSelectionProcess.setMaxLineagesToBuild(4);
        slotSelectionProcess.setSlotFunctionForRegimes(slotFunctionForRegimes());
        slotSelectionProcess.setFitnessFunctionForRegimes(fitnessFunctionForRegimes());
        slotSelectionProcess.setMaxResponseSource(lineageMaxResponseSource());
        return slotSelectionProcess;
    }

    @Bean
    public UnivariateRealFunction slotFunctionForLineage() {
        List<Point2d> controlPoints = new ArrayList<>();
        controlPoints.add(new Point2d(0.0, 0.1));
        controlPoints.add(new Point2d(1.0, 0.1));
        controlPoints.add(new Point2d(1.0, 0.33));
        controlPoints.add(new Point2d(2.0, 0.66));
        controlPoints.add(new Point2d(3.99, 1.0));
        controlPoints.add(new Point2d(4.0, 0.0));
        return new LinearSpline(controlPoints);
    }


//    @Bean
//    public UnivariateRealFunction slotFunctionForLineage() {
//        List<Point2d> controlPoints = new ArrayList<>();
//        controlPoints.add(new Point2d(0.0, 0.001));
//        controlPoints.add(new Point2d(1.0, 0.001));
//        controlPoints.add(new Point2d(1.0, 0.5));
//        controlPoints.add(new Point2d(2.0, 1.5));
//        controlPoints.add(new Point2d(3.9, 4.5));
//        controlPoints.add(new Point2d(4.0, 0.0));
//        return new LinearSpline(controlPoints);
//    }


    @Bean
    public Map<Regime, UnivariateRealFunction> slotFunctionForRegimes() {
        Map<Regime, UnivariateRealFunction> slotFunctionForRegimes = new HashMap<>();
        slotFunctionForRegimes.put(Regime.ZERO, new UnivariateRealFunction() {
            @Override
            public double value(double v) throws FunctionEvaluationException {
                if (v < 1.0){
                    return 0.3;
                } else {
                    return 0.0;
                }
            }
        });
        slotFunctionForRegimes.put(Regime.ONE, squareFunction(1.0, 2.0));
        slotFunctionForRegimes.put(Regime.TWO, squareFunction(2.0, 3.0));
        slotFunctionForRegimes.put(Regime.THREE, squareFunction(3.0, 4.0));
        return slotFunctionForRegimes;
    }

    public UnivariateRealFunction squareFunction(double left, double right){
        List<Point2d> controlPoints = new ArrayList<>();
        controlPoints.add(new Point2d(left, 0));
        controlPoints.add(new Point2d(left, 1));
        controlPoints.add(new Point2d(right, 1));
        controlPoints.add(new Point2d(right, 0));
        return new LinearSpline(controlPoints);
    }

//    @Bean
//    public Map<Regime, UnivariateRealFunction> slotFunctionForRegimes() {
//        Map<Regime, UnivariateRealFunction> slotFunctionForRegimes = new HashMap<>();
//        slotFunctionForRegimes.put(Regime.ZERO, new UnivariateRealFunction() {
//            @Override
//            public double value(double v) throws FunctionEvaluationException {
//                if (v < 1.0){
//                return 0.3;
//                } else {
//                    return 0.0;
//                }
//            }
//        });
//        slotFunctionForRegimes.put(Regime.ONE, truncated_peak(1.0));
//        slotFunctionForRegimes.put(Regime.TWO, peakFunctionAround(2.0, 1.0));
//        slotFunctionForRegimes.put(Regime.THREE, peakFunctionAround(3.0, 1.0));
//        return slotFunctionForRegimes;
//    }

    private UnivariateRealFunction truncated_peak(double left_edge) {
        return new UnivariateRealFunction() {
            @Override
            public double value(double v) throws FunctionEvaluationException {
                if (v<left_edge){
                    return 0.0;
                } else{
                    return peakFunctionAround(left_edge, 1.0).value(v);
                }
            }
        };
    }


    public UnivariateRealFunction peakFunctionAround(double center, double radius) {
        List<Point2d> controlPoints = new ArrayList<>();
        controlPoints.add(new Point2d(center - radius, 0));
        controlPoints.add(new Point2d(center, 1));
        controlPoints.add(new Point2d(center + radius, 0));
        return new NaturalSpline(controlPoints);
    }

    @Bean
    public Map<Regime, UnivariateRealFunction> fitnessFunctionForRegimes() {
        Map<Regime, UnivariateRealFunction> fitnessFunctionsForRegimes = new HashMap<>();
        fitnessFunctionsForRegimes.put(Regime.ZERO, new UnivariateRealFunction() {
            @Override
            public double value(double v) throws FunctionEvaluationException {
                return 1.0;
            }
        });
        fitnessFunctionsForRegimes.put(Regime.ONE, fitnessFunctionForRegimeOne());
        fitnessFunctionsForRegimes.put(Regime.TWO, fitnessFunctionForRegimeTwo());
        fitnessFunctionsForRegimes.put(Regime.THREE, fitnessFunctionForRegimeThree());
        return fitnessFunctionsForRegimes;
    }

    @Bean
    public UnivariateRealFunction fitnessFunctionForRegimeOne() {
        return new Sigmoid(0.5, 10.0);
    }

    @Bean
    public UnivariateRealFunction fitnessFunctionForRegimeTwo() {
        return  new Sigmoid(0.8, 50.0);
    }

    @Bean
    public UnivariateRealFunction fitnessFunctionForRegimeThree() {
        List<Point2d> controlPoints = new ArrayList<>();
        controlPoints.add(new Point2d(0, 0));
        controlPoints.add(new Point2d(0.75, 0));
        controlPoints.add(new Point2d(0.75, 1.0));
        controlPoints.add(new Point2d(1.0, 1.0));
        return new LinearSpline(controlPoints);
    }

    @Bean
    public UnivariateRealFunction zeroFunction() {
        return new UnivariateRealFunction() {
            @Override
            public double value(double v) {
                return 0;
            }
        };
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
        zeroToOne.setMaxThresholdSource(regimeZeroToOneMaxSpikeRateThreshold());
        return zeroToOne;
    }

    @Bean
    public ValueSource regimeZeroToOneMaxSpikeRateThreshold() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 20.0;
            }
        };
    }

    @Bean
    public LineageScoreSource regimeOneToTwo() {
        StabilityOfMaxScoreSource oneToTwo = new StabilityOfMaxScoreSource();
        oneToTwo.setDbUtil(dbUtil());
        oneToTwo.setSpikeRateSource(spikeRateSource());
        oneToTwo.setMaxResponseSource(maxResponseSource());
        oneToTwo.setNormalizedRangeThresholdSource(regimeOneToTwoRangeThreshold());
        return oneToTwo;
    }

    @Bean
    public ValueSource regimeOneToTwoRangeThreshold() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 10.0;
            }
        };
    }

    @Bean
    public LineageScoreSource regimeTwoToThree() {
        ParentChildThresholdScoreSource twoToThree = new ParentChildThresholdScoreSource();
        twoToThree.setStimType(NewGABlockGenerator.stimTypeForRegime.get(Regime.TWO));
        twoToThree.setDbUtil(dbUtil());
        twoToThree.setNumPairThresholdSource(regimeTwoToThreePairThreshold());
        twoToThree.setParentResponseThresholdSource(regimeTwoToThreeParentThreshold());
        twoToThree.setChildResponseThresholdSource(regimeTwoToThreeChildThreshold());
        twoToThree.setSpikeRateSource(spikeRateSource());
        return twoToThree;
    }


    @Bean
    public ValueSource regimeTwoToThreePairThreshold() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 10.0;
            }
        };
    }

    @Bean
    public LineageValueSource regimeTwoToThreeParentThreshold() {
        return new LineageValueSource() {
            @Override
            public double getValue(long lineageId) {
                return 0.66 * lineageMaxResponseSource().getValue(lineageId);
            }
        };
    }

    @Bean
    public LineageValueSource regimeTwoToThreeChildThreshold() {
        return regimeTwoToThreeParentThreshold();
    }

    @Bean
    public LineageScoreSource regimeThreeToFour() {
        ParentChildBinThresholdsScoreSource threeToFour = new ParentChildBinThresholdsScoreSource();
        threeToFour.setStimType(NewGABlockGenerator.stimTypeForRegime.get(Regime.THREE));
        threeToFour.setDbUtil(dbUtil());
        threeToFour.setParentResponseThresholdSource(regimeThreeToFourParentThreshold());
        threeToFour.setNumPairThresholdSourcesForBins(regimeThreeToFourPairThresholds());
        threeToFour.setSpikeRateSource(spikeRateSource());
        threeToFour.setMaxResponseSource(lineageMaxResponseSource());
        return threeToFour;
    }

    @Bean
    public LineageValueSource regimeThreeToFourParentThreshold() {
        return new LineageValueSource() {
            @Override
            public double getValue(long lineageId) {
                return 0.66 * lineageMaxResponseSource().getValue(lineageId);
            }
        };
    }

    @Bean
    public Map<NormalizedResponseBin, ValueSource> regimeThreeToFourPairThresholds() {
        Map<NormalizedResponseBin, ValueSource> pairThresholds = new HashMap<>();
        pairThresholds.put(new NormalizedResponseBin(0.0, 0.33), thresholdForRegimeThreeToFourPair());
        pairThresholds.put(new NormalizedResponseBin(0.33, 0.66), thresholdForRegimeThreeToFourPair());
        pairThresholds.put(new NormalizedResponseBin(0.66, 1.0), thresholdForRegimeThreeToFourPair());
        return pairThresholds;
    }

    @Bean
    public ValueSource thresholdForRegimeThreeToFourPair() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 5.0;
            }
        };
    }

    @Bean(scope= BeanDefinition.SCOPE_SINGLETON)
    public MaxResponseSource maxResponseSource() {
        MaxResponseSource maxResponseSource = new MaxResponseSource();
        maxResponseSource.setDbUtil(dbUtil());
        maxResponseSource.setMinimumMaxResponse(30.0);
        maxResponseSource.setSpikeRateSource(spikeRateSource());
        return maxResponseSource;
    }

    @Bean(scope= BeanDefinition.SCOPE_SINGLETON)
    public LineageMaxResponseSource lineageMaxResponseSource() {
        LineageMaxResponseSource maxResponseSource = new LineageMaxResponseSource();
        maxResponseSource.setDbUtil(dbUtil());
        maxResponseSource.setMinimumMaxResponse(30.0);
        maxResponseSource.setSpikeRateSource(spikeRateSource());
        return maxResponseSource;
    }

    @Bean(lazy = Lazy.TRUE)
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