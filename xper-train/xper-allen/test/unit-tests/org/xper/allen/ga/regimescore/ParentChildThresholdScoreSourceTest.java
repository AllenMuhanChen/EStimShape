package org.xper.allen.ga.regimescore;

import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga.SpikeRateSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.ArrayList;
import java.util.List;

import static org.junit.Assert.*;

public class ParentChildThresholdScoreSourceTest {

    private ParentChildThresholdScoreSource source;

    @Before
    public void setUp() throws Exception {
        source = new ParentChildThresholdScoreSource();
        source.setStimType("Regime2");
        source.setDbUtil(new MockDbUtil());
        source.setNumPairThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 3.0;
            }
        });
        source.setSpikeRateSource(new SpikeRateSource() {
            @Override
            public Double getSpikeRate(Long stimId) {
                return stimId.doubleValue();
            }
        });
    }

    /**
     * Only pairs (parent, child) that pass are (4,8) and (5,10) soley because of the child threshold.
     *
     * The number of pair threshold is 3.
     *
     * So score = 2/3 = 0.666
     */
    @Test
    public void child_threshold_works() {
        source.setParentResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 0.0;
            }
        });
        source.setChildResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 8.0;
            }
        });
        Double actualScore = source.getLineageScore(1L);

        assertEquals(0.666, actualScore, 0.001);
    }

    /**
     * Only pairs (parent, child) that pass are (4,8) and (5,10) soley because of the parent threshold.
     */
    @Test
    public void parent_threshold_works() {
        source.setParentResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 3.5;
            }
        });
        source.setChildResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 0.0;
            }
        });
        Double actualScore = source.getLineageScore(1L);

        assertEquals(0.666, actualScore, 0.001);
    }

    /**
     * All five pairs pass
     */
    @Test
    public void more_pairs_than_threshold_leads_to_score_of_one() {
        source.setParentResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 0.0;
            }
        });
        source.setChildResponseThresholdSource(new ThresholdSource() {
            @Override
            public Double getThreshold() {
                return 0.0;
            }
        });
        Double actualScore = source.getLineageScore(1L);

        assertEquals(1, actualScore, 0.001);
    }

    /**
     * There's 5 pairs of (parent, child).
     * (1,2), (2,4), (3,6), (4,8), (5,10)
     */
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
            return stimIds;
        }

        @Override
        public Long readParentFor(Long stimId) {
            return stimId/2;
        }
    }
}