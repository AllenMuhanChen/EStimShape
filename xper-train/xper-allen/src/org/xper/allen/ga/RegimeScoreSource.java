package org.xper.allen.ga;

import org.xper.Dependency;
import org.xper.allen.ga3d.blockgen.LineageData;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.Map;

public class RegimeScoreSource implements LineageScoreSource{

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions;

    private Double regimeScore;
    private Double lastGenRegimeScore;

    public enum RegimeTransition{
        ZERO_TO_ONE,
        ONE_TO_TWO,
        TWO_TO_THREE,
        THREE_TO_FOUR,
    }
    public Double getLineageScore(Long lineageId) {
        lastGenRegimeScore = dbUtil.readRegimeScore(lineageId);
        calculateRegimeScore(lineageId);
        updateRegimeScore(lineageId);
        return regimeScore;
    }

    private void calculateRegimeScore(Long founderId) {
        Double lineageScore;
        if (lastGenRegimeScore < 1.0){
            lineageScore = calculateLineageScoreWith(RegimeTransition.ZERO_TO_ONE, founderId);
            regimeScore = 1.0 + lineageScore;
        }
        else if (lastGenRegimeScore < 2.0){
            lineageScore = calculateLineageScoreWith(RegimeTransition.ONE_TO_TWO, founderId);
            regimeScore = 2.0 + lineageScore;
        }
        else if (lastGenRegimeScore < 3.0) {
            lineageScore = calculateLineageScoreWith(RegimeTransition.TWO_TO_THREE, founderId);
            regimeScore = 3.0 + lineageScore;
        }
        else if (lastGenRegimeScore < 4.0) {
            lineageScore = calculateLineageScoreWith(RegimeTransition.THREE_TO_FOUR, founderId);
            regimeScore = 4.0 + lineageScore;
        }
    }

    private Double calculateLineageScoreWith(RegimeTransition regimeTransition, Long founderId){
        Double newRegimeScore = lineageScoreSourceForRegimeTransitions.get(regimeTransition).getLineageScore(founderId);
        if (newRegimeScore > lastGenRegimeScore){
            return newRegimeScore;
        } else {
            return lastGenRegimeScore;
        }
    }

    private void updateRegimeScore(Long lineageId) {
        dbUtil.updateRegimeScore(lineageId, regimeScore);
        LineageData lineageData = updateLineageData(lineageId);
        dbUtil.writeLineageData(lineageId, lineageData.toXml());
    }

    private LineageData updateLineageData(Long lineageId) {
        LineageData lineageData;
        try {
            lineageData = LineageData.fromXml(dbUtil.readLineageData(lineageId));
        } catch (RuntimeException e){
            lineageData = new LineageData();
        }
        lineageData.putRegimeScoreForGeneration(dbUtil.readLatestGenIdForLineage(lineageId), regimeScore);
        return lineageData;
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