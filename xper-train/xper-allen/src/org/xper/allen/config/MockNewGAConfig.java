package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.ga.*;
import org.xper.allen.ga.regimescore.*;
import org.xper.allen.ga.regimescore.ParentChildBinThresholdsScoreSource.NormalizedResponseBin;
import org.xper.allen.newga.blockgen.SlotGABlockGenerator;
import org.xper.classic.SlideEventListener;
import org.xper.classic.SlideTrialRunner;
import org.xper.classic.TrialEventListener;
import org.xper.config.ClassicConfig;
import org.xper.experiment.listener.ExperimentEventListener;

import java.util.HashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

@Configuration(defaultLazy = Lazy.TRUE)
@SystemPropertiesValueSource
@AnnotationDrivenConfig
@Import({NewGAConfig.class})
public class MockNewGAConfig {
    @Autowired
    NewGAConfig config;
    @Autowired
    ClassicConfig classicConfig;

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public List<ExperimentEventListener> experimentEventListeners () {
        List<ExperimentEventListener> listeners =  new LinkedList<ExperimentEventListener>();
        listeners.add(classicConfig.messageDispatcher());
        listeners.add(classicConfig.databaseTaskDataSourceController());
        listeners.add(classicConfig.messageDispatcherController());
        return listeners;
    }

    @Bean(scope = DefaultScopes.PROTOTYPE)
    public List<SlideEventListener> slideEventListeners () {
        List<SlideEventListener> listeners = new LinkedList<SlideEventListener>();
        listeners.add(classicConfig.messageDispatcher());
        return listeners;
    }

    @Bean (scope = DefaultScopes.PROTOTYPE)
    public List<TrialEventListener> trialEventListeners () {
        List<TrialEventListener> trialEventListener = new LinkedList<TrialEventListener>();
        trialEventListener.add(classicConfig.messageDispatcher());

        return trialEventListener;
    }

    @Bean
    public SlideTrialRunner slideTrialRunner(){
        MockSlideTrialRunner slideTrialRunner = new MockSlideTrialRunner();
        slideTrialRunner.setSlideRunner(slideRunner());
        return slideTrialRunner;
    }

    @Bean
    public MockClassicSlideRunner slideRunner() {
        return new MockClassicSlideRunner();
    }


    @Bean
    public MockSpikeRateSource spikeRateSource(){
        MockSpikeRateSource spikeRateSource = new MockSpikeRateSource();
        spikeRateSource.setDbUtil(config.dbUtil());
        spikeRateSource.setGaName(SlotGABlockGenerator.gaBaseName);
        return spikeRateSource;
    }

    /**
     * Threshold on max spike rate. When spike rate meets or exceeds this threshold, the score is 1.
     * @return
     */
    @Bean
    public ValueSource regimeZeroToOneMaxSpikeRateThreshold() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 30.0;
            }
        };
    }

    /**
     * Threshold on the max range between the most recent N stimuli in a lineage.
     * When the range meets or exceeds this threshold, the score is 1.
     * @return
     */
    @Bean
    public ValueSource regimeOneToTwoRangeThreshold() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 10.0;
            }
        };
    }

    /**
     * Threshold on the number of parent-child pairs that meet response thresholds
     * for the parents and children, respectively.
     */
    @Bean
    public ValueSource regimeTwoToThreePairThreshold() {
        return new ValueSource() {
            @Override
            public Double getValue() {
                return 3.0;
            }
        };
    }


//    @Bean
//    public LineageScoreSource regimeThreeToFour() {
//        StabilityOfMaxScoreSource oneToTwo = new StabilityOfMaxScoreSource();
//        oneToTwo.setDbUtil(config.dbUtil());
//        oneToTwo.setSpikeRateSource(spikeRateSource());
//        oneToTwo.setMaxResponseSource(config.maxResponseSource());
//        oneToTwo.setNormalizedRangeThresholdSource(regimeThreeToFourRangeThreshold());
//        oneToTwo.setN(6);
//        oneToTwo.setStimType(STIM_TYPE_FOR_REGIME.get(Regime.THREE));
//        return oneToTwo;
//    }

//    @Bean
//    public ValueSource regimeThreeToFourRangeThreshold() {
//        return new ValueSource() {
//            @Override
//            public Double getValue() {
//                return 5.0;
//            }
//        };
//    }

    /**
     * Threshold for the bin distribution of the children to be considered for a parent-child pair.
     * @return
     */
    @Bean
    public Map<NormalizedResponseBin, ValueSource> regimeThreeToFourPairThresholds() {
        Map<NormalizedResponseBin, ValueSource> pairThresholds = new HashMap<>();
        pairThresholds.put(new NormalizedResponseBin(0.0, 0.33), new ValueSource() {
            @Override
            public Double getValue() {
                return 5.0;
            }
        });
        pairThresholds.put(new NormalizedResponseBin(0.33, 0.66), new ValueSource() {
            @Override
            public Double getValue() {
                return 5.0;
            }
        });
        pairThresholds.put(new NormalizedResponseBin(0.66, 1.0), new ValueSource() {
            @Override
            public Double getValue() {
                return 3.0;
            }
        });
        return pairThresholds;
    }


}