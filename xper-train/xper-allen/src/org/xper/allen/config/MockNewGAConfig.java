package org.xper.allen.config;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.config.java.annotation.*;
import org.springframework.config.java.annotation.valuesource.SystemPropertiesValueSource;
import org.springframework.config.java.plugin.context.AnnotationDrivenConfig;
import org.springframework.config.java.util.DefaultScopes;
import org.xper.allen.ga.*;
import org.xper.allen.ga.regimescore.ParentChildBinThresholdsScoreSource.NormalizedResponseBin;
import org.xper.allen.ga.regimescore.ThresholdSource;
import org.xper.allen.newga.blockgen.NewGABlockGenerator;
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
        spikeRateSource.setGaName(NewGABlockGenerator.gaBaseName);
        return spikeRateSource;
    }

    /**
     * Threshold on max spike rate. When spike rate meets or exceeds this threshold, the score is 1.
     * @return
     */
    @Bean
    public ThresholdSource regimeZeroToOneMaxSpikeRateThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
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
    public ThresholdSource regimeOneToTwoRangeThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 10.0;
            }
        };
    }

    /**
     * Threshold on the number of parent-child pairs that meet response thresholds
     * for the parents and children, respectively.
     */
    @Bean
    public ThresholdSource regimeTwoToThreePairThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 4.0;
            }
        };
    }

    /**
     * Threshold for the response of parents to be considered for a parent-child pair.
     * @return
     */
    @Bean
    public ThresholdSource regimeTwoToThreeParentThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return getCurrentMaxResponse()*0.75;
            }
        };
    }

    private double getCurrentMaxResponse() {
        return config.maxResponseSource().getMaxResponse(NewGABlockGenerator.gaBaseName);
    }

    @Bean
    public ThresholdSource regimeTwoToThreeChildThreshold() {
        return regimeTwoToThreeParentThreshold();
    }


    /**
     * Threshold on the response rate that parents must meet to be considered for a parent-child pair.
     * @return
     */
    @Bean
    public ThresholdSource regimeThreeToFourParentThreshold() {
        return new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return getCurrentMaxResponse()*0.75;
            }
        };
    }

    /**
     * Threshold for the bin distribution of the children to be considered for a parent-child pair.
     * @return
     */
    @Bean
    public Map<NormalizedResponseBin, ThresholdSource> regimeThreeToFourPairThresholds() {
        Map<NormalizedResponseBin, ThresholdSource> pairThresholds = new HashMap<>();
        pairThresholds.put(new NormalizedResponseBin(0.0, 0.33), new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 10.0;
            }
        });
        pairThresholds.put(new NormalizedResponseBin(0.33, 0.66), new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 5.0;
            }
        });
        pairThresholds.put(new NormalizedResponseBin(0.66, 1.0), new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 3.0;
            }
        });
        return pairThresholds;
    }


}