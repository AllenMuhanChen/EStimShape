package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.Map;

public class RegimeScoreSource implements LineageScoreSource{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions;

    private Double regimeScore;

    public enum RegimeTransition{
        ZERO_TO_ONE,
        ONE_TO_TWO,
        TWO_TO_THREE,
        THREE_TO_FOUR,
    }
    public Double getLineageScore(Long lineageId) {
        regimeScore = dbUtil.readRegimeScore(lineageId);
        calculateRegimeScore(lineageId);
        dbUtil.updateRegimeScore(lineageId, regimeScore);
        return regimeScore;
    }

    private void calculateRegimeScore(Long founderId) {
        if (regimeScore < 1.0){
            updateRegimeScoreWith(RegimeTransition.ZERO_TO_ONE, founderId);
        }
        else if (regimeScore < 2.0){
            updateRegimeScoreWith(RegimeTransition.ONE_TO_TWO, founderId);
        }
        else if (regimeScore < 3.0) {
            updateRegimeScoreWith(RegimeTransition.TWO_TO_THREE, founderId);
        }
        else if (regimeScore < 4.0) {
            updateRegimeScoreWith(RegimeTransition.THREE_TO_FOUR, founderId);
        }
    }

    private void updateRegimeScoreWith(RegimeTransition regimeTransition, Long founderId){
        Double newRegimeScore = lineageScoreSourceForRegimeTransitions.get(regimeTransition).getLineageScore(founderId);
        if (newRegimeScore > regimeScore){
            regimeScore = newRegimeScore;
        }
    }

    public MultiGaDbUtil getDbUtil() {
        return dbUtil;
    }

    public void setDbUtil(MultiGaDbUtil dbUtil) {
        this.dbUtil = dbUtil;
    }

    public Map<RegimeTransition, LineageScoreSource> getLineageScoreSourceForRegimeTransitions() {
        return lineageScoreSourceForRegimeTransitions;
    }

    public void setLineageScoreSourceForRegimeTransitions(Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions) {
        this.lineageScoreSourceForRegimeTransitions = lineageScoreSourceForRegimeTransitions;
    }
}