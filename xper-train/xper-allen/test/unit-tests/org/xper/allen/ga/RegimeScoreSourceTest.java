package org.xper.allen.ga;

import org.junit.Test;
import org.xper.allen.util.MultiGaDbUtil;

public class RegimeScoreSourceTest {

    @Test
    public void getRegimeScoreForLineages() {
        RegimeScoreSource regimeScoreSource = new RegimeScoreSource();
        regimeScoreSource.setDbUtil(new RegimeScoreSourceTestDbUtil());

        Double score = regimeScoreSource.getLineageScore(1L);
    }

    private class RegimeScoreSourceTestDbUtil extends MultiGaDbUtil {

    }
}