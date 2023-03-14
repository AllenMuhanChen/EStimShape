package org.xper.allen.ga.regimescore;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class MaxValueLineageScoreTest {

    private MaxValueLineageScore source;

    @Before
    public void setUp() throws Exception {
        source = new MaxValueLineageScore();

        source.setDbUtil(new MockDbUtil());
        source.setSpikeRateSource(new MockSpikeRateSource());
        source.setMaxThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 3.0;
            }
        });
    }

    @Test
    public void under_threshold_returns_right_value(){
        source.setDbUtil(new MockDbUtil() {
            @Override
            public List<Long> readStimIdsFromLineageAndType(Long lineageId, String type) {
                List<Long> stimIds = new ArrayList<Long>();
                stimIds.add(1L);
                stimIds.add(2L);
                return stimIds;
            }
        });

        Double score = source.getLineageScore(null);
        assertEquals(0.6666, score, 0.001);
    }

    @Test
    public void over_threshold_returns_1() {
        source.setDbUtil(new MockDbUtil() {
            @Override
            public List<Long> readStimIdsFromLineageAndType(Long lineageId, String type) {
                List<Long> stimIds = new ArrayList<Long>();
                stimIds.add(1L);
                stimIds.add(2L);
                stimIds.add(3L);
                stimIds.add(4L);
                return stimIds;
            }
        });
        Double score = source.getLineageScore(null);
        assertEquals(1, score, 0.001);

    }

    private static class MockDbUtil extends MultiGaDbUtil {

    }

    private static class MockSpikeRateSource implements SpikeRateSource {
        @Override
        public List<Double> getSpikeRates(Long taskId) {
            List<Double> spikeRates = new ArrayList<Double>();
            spikeRates.add(Double.valueOf(taskId));
            return spikeRates;
        }
    }




}