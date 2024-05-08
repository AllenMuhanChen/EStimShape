//package org.xper.allen.ga.regimescore;
//
//import org.junit.Before;
//import org.junit.Test;
//import org.xper.allen.ga.regimescore.LineageScoreSource;
//import org.xper.allen.ga.regimescore.RegimeScoreSource;
//import org.xper.allen.ga3d.blockgen.LineageData;
//import org.xper.allen.util.MultiGaDbUtil;
//
//import java.util.LinkedHashMap;
//import java.util.Map;
//
//import static org.junit.Assert.assertEquals;
//
//public class MutationTypeScoreSourceTest {
//
//    private RegimeScoreSource regimeScoreSource;
//
//    @Before
//    public void setUp() throws Exception {
//        regimeScoreSource = new RegimeScoreSource();
//        regimeScoreSource.setDbUtil(new RegimeScoreSourceTestDbUtil());
//
//        regimeScoreSource.setLineageScoreSourceForRegimeTransitions(lineageScoreSourcesForRegimeTransitions());
//    }
//
//    private Map<RegimeScoreSource.RegimeTransition, LineageScoreSource> lineageScoreSourcesForRegimeTransitions() {
//        Map<RegimeScoreSource.RegimeTransition, LineageScoreSource> map = new LinkedHashMap<>();
//        map.put(RegimeScoreSource.RegimeTransition.ZERO_TO_ONE, new LineageScoreSource() {
//            @Override
//            public Double getLineageScore(Long lineageId) {
//                return 1.0;
//            }
//        });
//
//        map.put(RegimeScoreSource.RegimeTransition.ONE_TO_TWO, new LineageScoreSource() {
//            @Override
//            public Double getLineageScore(Long lineageId) {
//                return 4.0;
//            }
//        });
//
//        map.put(RegimeScoreSource.RegimeTransition.TWO_TO_THREE, new LineageScoreSource() {
//            @Override
//            public Double getLineageScore(Long lineageId) {
//                return 9.0;
//            }
//        });
//
//        map.put(RegimeScoreSource.RegimeTransition.THREE_TO_FOUR, new LineageScoreSource() {
//            @Override
//            public Double getLineageScore(Long lineageId) {
//                return 16.0;
//            }
//        });
//
//        return map;
//    }
//
//    @Test
//    public void regime_scores_calls_correct_lineage_score_source() {
//        Double score = regimeScoreSource.getLineageScore(0L);
//        assertEquals(1.0, score, 0.0001);
//
//        score = regimeScoreSource.getLineageScore((long) 0.5);
//        assertEquals(1.0, score, 0.0001);
//
//        score = regimeScoreSource.getLineageScore(1L);
//        assertEquals(4.0+1, score, 0.0001);
//
//        score = regimeScoreSource.getLineageScore(2L);
//        assertEquals(9+2, score, 0.0001);
//
//        score = regimeScoreSource.getLineageScore(3L);
//        assertEquals(16.0+3, score, 0.0001);
//    }
//
//    @Test
//    public void regime_scores_saved_in_lineage_data(){
//        regimeScoreSource.getLineageScore(2L);
//
//        String lineageDataXml = regimeScoreSource.getDbUtil().readLineageData(2L);
//        LineageData lineageData = LineageData.fromXml(lineageDataXml);
//
//        assertEquals(9.0+2, lineageData.regimeScoreForGenerations.get(10), 0.0001);
//    }
//
//    @Test
//    public void getLineageScore() {
//    }
//
//    /**
//     * Sets regime score of previous generation to be the lineage id of the current generation for testing purposes
//     */
//    private static class RegimeScoreSourceTestDbUtil extends MultiGaDbUtil {
//
//        Map<Long, LineageData> dataForLineages = new LinkedHashMap<>();
//
//        @Override
//        public Double readRegimeScore(Long lineageId) {
//            return lineageId.doubleValue();
//        }
//
//        @Override
//        public void updateRegimeScore(Long lineageId, Double regimeScore) {
//            //empty
//        }
//
//        @Override
//        public String readLineageData(Long lineageId) {
//            return dataForLineages.get(lineageId).toXml();
//        }
//
//        @Override
//        public Integer readLatestGenIdForLineage(Long lineageId) {
//            return 10;
//        }
//
//        @Override
//        public void writeLineageData(Long lineageId, String xml) {
//            LineageData data = LineageData.fromXml(xml);
//            dataForLineages.put(lineageId, data);
//        }
//    }
//
//
//}