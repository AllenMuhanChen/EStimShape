package org.xper.allen.ga.regimescore;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga.MaxResponseSource;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.*;

import static org.junit.Assert.*;

public class StabilityOfMaxSourceTest {

    private StabilityOfMaxSource source;

    @Before
    public void setUp() throws Exception {
        source = new StabilityOfMaxSource();
        source.setDbUtil(new MockDbUtil());
        source.setSpikeRateSource(new MockSpikeRateSource());
        source.setMaxResponseSource(new MockMaxResponseSource());
        source.setNormalizedRangeThresholdSource(new MockNormalizedRangeThresholdSource());
    }

    /**
     * gen1: max=3
     * gen2: max=6
     * gen3: max=9
     *
     * range = 9-3 = 6
     * rangeThreshold = 0.2*10 = 2
     * stability = rangeThresh / range = 2/6
     * score = 0.333
     *
     */
    @Test
    public void under_threshold_returns_between_0_and_1() {
        Double actualScore = source.getLineageScore(1L);
        assertEquals(0.333, actualScore, 0.001);
    }

    /**
     * gen1: max=8
     * gen2: max=9
     * gen3: max=10
     *
     * range = 10-8 = 2
     * rangeThreshold = 0.2*10 = 2
     * stability = rangeThresh / range = 2/2
     * score = 1
     */
    @Test
    public void at_threshold_returns_1(){
        Double actualScore = source.getLineageScore(2L);
        assertEquals(1.0, actualScore, 0.001);
    }

    /**
     * gen1: max=9
     * gen2: max=9
     * gen3: max=10
     *
     * range = 10-9 = 1
     * rangeThreshold = 0.2*10 = 2
     * stability = rangeThresh / range = 2/1
     * score = 1
     */
    @Test
    public void over_threshold_returns_1(){
        Double actualScore = source.getLineageScore(3L);
        assertEquals(1.0, actualScore, 0.001);
    }
    private static class MockDbUtil extends MultiGaDbUtil {

        @Override
        public Map<Integer, List<Long>> readStimIdsFromGenIdsFor(Long lineageId){
            Map<Integer, List<Long>> map = new LinkedHashMap<>();
            if (lineageId.equals(1L)) {
                map.put(1, Arrays.asList(1L, 2L, 3L));
                map.put(2, Arrays.asList(4L, 5L, 6L));
                map.put(3, Arrays.asList(7L, 8L, 9L));

            }
            else if (lineageId.equals(2L)) {
                map.put(1, Arrays.asList(1L, 2L, 8L));
                map.put(2, Arrays.asList(4L, 5L, 9L));
                map.put(3, Arrays.asList(7L, 8L, 10L));
            }
            else if (lineageId.equals(3L)) {
                map.put(1, Arrays.asList(1L, 2L, 9L));
                map.put(2, Arrays.asList(4L, 5L, 9L));
                map.put(3, Arrays.asList(7L, 8L, 10L));
            }
            return map;
        }

        @Override
        public String readGaNameFor(Long lineageId) {
            return "test";
        }
    }

    private static class MockSpikeRateSource implements SpikeRateSource {
        @Override
        public Double getSpikeRate(Long taskId) {
            return taskId.doubleValue();
        }
    }

    private static class MockMaxResponseSource extends MaxResponseSource {
        @Override
        public double getMaxResponse(String gaName) {
            return 10.0;
        }
    }

    private static class MockNormalizedRangeThresholdSource implements ThresholdSource {
        @Override
        public Double getThreshold() {
            return 0.2;
        }
    }
}