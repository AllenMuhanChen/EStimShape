package org.xper.allen.ga.regimescore;

import org.xper.Dependency;
import org.xper.allen.ga3d.blockgen.LineageData;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.Map;

public class RegimeScoreSource implements LineageScoreSource {

    @Dependency
    MultiGaDbUtil dbUtil;

    @Dependency
    Map<RegimeTransition, LineageScoreSource> lineageScoreSourceForRegimeTransitions;

    private Double regimeScore;
    private Double lastGenRegimeScore;
    private Long lineageId;

    public enum RegimeTransition{
        ZERO_TO_ONE,
        ONE_TO_TWO,
        TWO_TO_THREE,
        THREE_TO_FOUR,
    }
    public Double getLineageScore(Long lineageId) {
        regimeScore = 0.0;
        this.lineageId = lineageId;
        lastGenRegimeScore = dbUtil.readRegimeScore(lineageId);
        calculateRegimeScore();
        updateRegimeScore();
        saveLineageData();
        return regimeScore;
    }

    private void calculateRegimeScore() {
        Double lineageScore;
        if (lastGenRegimeScore < 1.0){
            lineageScore = calculateLineageScoreWith(RegimeTransition.ZERO_TO_ONE, lineageId);
            System.out.println("Lineage score: " + lineageScore + " for transition: " + RegimeTransition.ZERO_TO_ONE);
            System.out.println(" for lineage: " + lineageId);
            regimeScore = lineageScore;
        }
        else if (lastGenRegimeScore < 2.0){
            lineageScore = calculateLineageScoreWith(RegimeTransition.ONE_TO_TWO, lineageId);
            System.out.println("Lineage score: " + lineageScore + " for transition: " + RegimeTransition.ONE_TO_TWO);
            System.out.println(" for lineage: " + lineageId);
            regimeScore = 1.0 + lineageScore;

        }
        else if (lastGenRegimeScore < 3.0) {
            lineageScore = calculateLineageScoreWith(RegimeTransition.TWO_TO_THREE, lineageId);
            System.out.println("Lineage score: " + lineageScore + " for transition: " + RegimeTransition.TWO_TO_THREE);
            regimeScore = 2.0 + lineageScore;
        }
        else if (lastGenRegimeScore < 4.0) {
            lineageScore = calculateLineageScoreWith(RegimeTransition.THREE_TO_FOUR, lineageId);
            System.out.println("Lineage score: " + lineageScore + " for transition: " + RegimeTransition.THREE_TO_FOUR);
            regimeScore = 3.0 + lineageScore;
        }
        else if (lastGenRegimeScore == 4.0){
            regimeScore = 4.0;
        }
        else {
            throw new RuntimeException("Regime score is greater than 4.0! " + lastGenRegimeScore);
        }
        if (regimeScore < lastGenRegimeScore){
            regimeScore = lastGenRegimeScore;
        }
        System.err.println("Regime score: " + regimeScore);
    }

    private Double calculateLineageScoreWith(RegimeTransition regimeTransition, Long founderId){
        return lineageScoreSourceForRegimeTransitions.get(regimeTransition).getLineageScore(founderId);
    }

    private void updateRegimeScore() {
        dbUtil.updateRegimeScore(this.lineageId, regimeScore);
    }

    private void saveLineageData() {
        LineageData lineageData = fetchLineageData();
        updateLineageDataRegimeScore(lineageData);
        dbUtil.writeLineageData(this.lineageId, lineageData.toXml());
    }

    private LineageData updateLineageDataRegimeScore(LineageData lineageData) {
        lineageData.putRegimeScoreForGeneration(dbUtil.readLatestGenIdForLineage(this.lineageId), regimeScore);
        return lineageData;
    }

    private LineageData fetchLineageData() {
        LineageData lineageData;
        try {
            lineageData = LineageData.fromXml(dbUtil.readLineageData(this.lineageId));
        } catch (RuntimeException e){
            lineageData = new LineageData();
        }
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