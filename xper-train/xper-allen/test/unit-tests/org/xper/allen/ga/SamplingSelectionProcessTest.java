//package org.xper.allen.ga;
//
//import org.junit.Before;
//import org.junit.Test;
//
//import java.util.ArrayList;
//import java.util.List;
//
//import static junit.framework.Assert.assertEquals;
//import static junit.framework.Assert.assertTrue;
//
//public class SamplingSelectionProcessTest {
//
//    private static final int NUM_DRAWS = 100000;
//    private SamplingSelectionProcess selector;
//
//    @Before
//    public void setUp() throws Exception {
//        selector = new SamplingSelectionProcess();
//
//        //Mock extraction from Database of children (stimIds). Random stimIds?
//        selector.setDbUtil(new ComplexParentSelectorTestDbUtil());
//        //Mock produce spike rates for each child based on the stimId
//        selector.setSpikeRateSource(new ComplexParentSelectorTestSpikeRateSource());
//        selector.setCanopyWidthSource(new ComplexParentSelectorTestCanopyWidthSource());
//        selector.setFitnessScoreCalculator(new ComplexParentSelectorTestFitnessScoreCalculator());
//        selector.setNumChildrenToSelect(NUM_DRAWS);
//    }
//
//    @Test
//    public void selects_correct_distribution_of_children() {
//
//        List<Child> selectedChildren = selector.select("test");
//
//        ProbabilityTable<Child> table = selector.getTable();
//        List<Child> possibleChildren = table.getItems();
//        List<Integer> possibleChildCounts = new ArrayList<>();
//        for (int i = 0; i < possibleChildren.size(); i++) {
//            possibleChildCounts.add(0);
//        }
//        for (Child child : selectedChildren) {
//            for (int i = 0; i < possibleChildren.size(); i++) {
//                if (child == possibleChildren.get(i)) {
//                    possibleChildCounts.set(i, possibleChildCounts.get(i) + 1);
//                }
//            }
//        }
//
//        //We have 10 stimIds, so 10*2 = 20 possible children.
//        assertEquals(20, possibleChildCounts.size());
//
//        //check that the number of times each child is selected is within 15% of the expected number of times.
//        for (int i = 0; i < possibleChildren.size(); i++) {
//            double expectedCount = table.getProbabilities().get(i) * NUM_DRAWS;
//            double actualCount = possibleChildCounts.get(i);
//            double percentError = Math.abs(expectedCount - actualCount) / expectedCount;
//            System.out.println("item: " + possibleChildren.get(i).getParentId() + " expectedCount: " + expectedCount + " actualCount: " + actualCount + " percentError: " + percentError);
//            assertTrue(percentError < 0.15);
//        }
//
//        //Check that the count ratio between two children is within 15% of the ratio of their stimIds
//        //This is because we hardcoded that the probability is directly-related to stimId
//        for (int i = 0; i < possibleChildren.size(); i++) {
//            for (int j = i + 1; j < possibleChildren.size(); j++) {
//                double expectedRatio = (double) possibleChildren.get(i).getParentId() / (double) possibleChildren.get(j).getParentId();
//                double actualRatio = (double) possibleChildCounts.get(i) / (double) possibleChildCounts.get(j);
//                double percentError = Math.abs(expectedRatio - actualRatio) / expectedRatio;
//                System.out.println("item: " + possibleChildren.get(i).getParentId() + " / " + possibleChildren.get(j).getParentId() + " expectedRatio: " + expectedRatio + " actualRatio: " + actualRatio + " percentError: " + percentError);
//                assertTrue(percentError < 0.15);
//            }
//        }
//
//
//    }
//
//
//
//    private static class ComplexParentSelectorTestFitnessScoreCalculator implements FitnessScoreCalculator<TreeFitnessScoreParameters> {
//
//        @Override
//        public  double calculateFitnessScore(TreeFitnessScoreParameters params) {
//            return params.getAverageSpikeRate() * params.getCanopyWidth();
//        }
//    }
//
//    private static class ComplexParentSelectorTestSpikeRateSource implements SpikeRateSource {
//        @Override
//        public Double getSpikeRate(Long stimId) {
//            return stimId.doubleValue();
//        }
//    }
//
//    private static class ComplexParentSelectorTestCanopyWidthSource extends CanopyWidthSource {
//        @Override
//        public Integer getCanopyWidth(Long stimId) {
//            return 1;
//        }
//    }
//}