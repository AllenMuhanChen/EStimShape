package org.xper.allen.ga.regimescore;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga.MaxResponseSource;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.ga.regimescore.ParentChildBinThresholdsScoreSource.NormalizedResponseBin;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.Assert.assertEquals;

public class ParentChildBinThresholdsScoreSourceTest {

    private ParentChildBinThresholdsScoreSource source;

    @Before
    public void setUp() throws Exception {
        source = new ParentChildBinThresholdsScoreSource();
        source.setStimType("test");
        source.setNumPairThresholdSourcesForBins(thresholdsForBins());
        source.setDbUtil(new MockDbUtil());
        source.setSpikeRateSource(new SpikeRateSource() {
            @Override
            public Double getSpikeRate(Long stimId) {
                return stimId.doubleValue();
            }
        });
        source.setParentResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 0.0;
            }
        });
        source.setMaxResponseSource(new MaxResponseSource() {
            @Override
            public double getMaxResponse(String gaName) {
                return 10.0;
            }
        });

    }

    private Map<NormalizedResponseBin, ThresholdSource> thresholdsForBins() {
        Map<NormalizedResponseBin, ThresholdSource> map = new LinkedHashMap<>();

        NormalizedResponseBin bin1 = new NormalizedResponseBin(0.0, 0.5);
        map.put(bin1, new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 3.0;
            }
        });

        NormalizedResponseBin bin2 = new NormalizedResponseBin(0.5, 1.0);
        map.put(bin2, new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 4.0;
            }
        });
        return map;
    }

    /**
     * There's 5 pairs of (parent, child).
     * (1,2), (2,4), (3,6), (4,8), (5,10)
     *
     * THe parent threshold is 0, so all of these pass the parent threshold
     *
     * There's two bins, 0-5 and 6-10 after being denormalized
     * First bin has two pairs compared the pair thresh of 3 --> score = 2/3 = 0.666
     * Third bin has three pairs compared to pair thresh of 4 --> score = 3/4 = 0.75
     *
     * Total score = (0.666 + 0.75) / 2 = 0.708
     */
    @Test
    public void test_correct_assigning_of_bins() {
        Double actualScore = source.getLineageScore(1L);
        assertEquals(0.708, actualScore, 0.001);
    }

    /**
     * There's 8 pairs of (parent, child).
     *
     * The first bin has two pairs compared pair thresh of 3 --> score = 2/3 = 0.666
     * The second bin has six pairs compared pair thresh of 4 --> score = 6/4 = 1.5
     *
     * Total score = (0.666 + 1.0) / 2 = 0.833
     */

    @Test
    public void more_pairs_in_one_bin_does_not_raise_whole_score(){
        Double actualScore = source.getLineageScore(2L);
        assertEquals(0.833, actualScore, 0.001);
    }


    private static class MockDbUtil extends MultiGaDbUtil {
        @Override
        public List<Long> readStimIdsFromLineageAndType(Long lineageId, String type) {
            List<Long> stimIds = new ArrayList<>();
            if (lineageId.equals(1L)) {
                stimIds.add(2L);
                stimIds.add(4L);
                stimIds.add(6L);
                stimIds.add(8L);
                stimIds.add(10L);
            }
            else if (lineageId.equals(2L)){
                stimIds.add(2L);
                stimIds.add(4L);
                stimIds.add(6L);
                stimIds.add(8L);
                stimIds.add(10L);
                stimIds.add(10L);
                stimIds.add(10L);
                stimIds.add(10L);
            }
            return stimIds;
        }

        @Override
        public Long readParentFor(Long stimId) {
            return stimId/2;
        }

        @Override
        public String readGaNameFor(Long stimId) {
        	return "test";
        }
    }
}