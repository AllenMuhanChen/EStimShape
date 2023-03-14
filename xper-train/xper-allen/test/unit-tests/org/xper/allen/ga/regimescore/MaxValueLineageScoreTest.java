package org.xper.allen.ga.regimescore;

import org.junit.Before;
import org.junit.Test;
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
    }

    @Test
    public void getLineageScore() {
        Double score = source.getLineageScore(1L);


    }

    private static class MockDbUtil extends MultiGaDbUtil {
        @Override
        public List<Long> readStimIdsFromLineageAndType(Long lineageId, String type) {
            List<Long> stimIds = new ArrayList<Long>();
            stimIds.add(1L);
            stimIds.add(2L);
            stimIds.add(3L);
            return stimIds;
        }
    }
}