package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.Map;

public class RegimeScoreSource implements LineageScoreSource{

    @Dependency
    MultiGaDbUtil dbUtil;


    @Dependency
    Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions;

    public enum RegimeTransition{
        ZERO_TO_ONE,
        ONE_TO_TWO,
        TWO_TO_THREE,
        THREE_TO_FOUR,
    }
    public Double getLineageScore(Long founderId) {
        Double regimeScore = dbUtil.readRegimeScore(founderId);
        return null;
    }



    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }


}