package org.xper.allen.ga;

import org.junit.Before;
import org.junit.Test;

import java.util.ArrayList;
import java.util.List;

import static junit.framework.Assert.assertEquals;
import static junit.framework.Assert.assertTrue;

public class SelectionProcessTest {

    private static final int NUM_DRAWS = 100000;
    private SelectionProcess selector;

    @Before
    public void setUp() throws Exception {
        selector = new SelectionProcess();

        //Mock extraction from Database of children (stimIds). Random stimIds?
        selector.setDbUtil(new ComplexParentSelectorTestDbUtil());
        //Mock produce spike rates for each child based on the stimId
        selector.setSpikeRateSource(new ComplexParentSelectorTestSpikeRateSource());
        selector.setCanopyWidthSource(new ComplexParentSelectorTestCanopyWidthSource());
        selector.setFitnessScoreCalculator(new ComplexParentSelectorTestFitnessScoreCalculator());
        selector.setNumChildren(NUM_DRAWS);
    }

    @Test
    public void selectParents() {

        List<Child> selectedChildren = selector.select("test");

        ProbabilityTable<Child> table = selector.getTable();
        List<Child> possibleChildren = table.getItems();
        List<Integer> possibleChildCounts = new ArrayList<>();
        for (int i = 0; i < possibleChildren.size(); i++) {
            possibleChildCounts.add(0);
        }
        for (Child child : selectedChildren) {
            for (int i = 0; i < possibleChildren.size(); i++) {
                if (child == possibleChildren.get(i)) {
                    possibleChildCounts.set(i, possibleChildCounts.get(i) + 1);
                }
            }
        }

        //We have 10 stimIds, so 10*2 = 20 possible children.
        assertEquals(20, possibleChildCounts.size());

        //check that the number of times each child is selected is within 10% of the expected number of times.
        for (int i = 0; i < possibleChildren.size(); i++) {
            double expectedCount = table.getProbabilities().get(i) * NUM_DRAWS;
            double actualCount = possibleChildCounts.get(i);
            double percentError = Math.abs(expectedCount - actualCount) / expectedCount;
            System.out.println("expectedCount: " + expectedCount + " actualCount: " + actualCount + " percentError: " + percentError);
            assertTrue(percentError < 0.1);
        }

    }





    private static class ComplexParentSelectorTestFitnessScoreCalculator implements FitnessScoreCalculator {
        @Override
        public double calculateFitnessScore(FitnessScoreParameters params) {
            return params.getAverageSpikeRate() * params.getTreeCanopyWidth();
        }
    }

    private static class ComplexParentSelectorTestSpikeRateSource implements SpikeRateSource {
        @Override
        public List<Double> getSpikeRates(Long taskId) {
            ArrayList<Double> output = new ArrayList<Double>();
            output.add(Double.valueOf(taskId));

            return output;
        }
    }

    private static class ComplexParentSelectorTestCanopyWidthSource extends CanopyWidthSource {
        @Override
        public Integer getCanopyWidth(Long stimId) {
            return 1;
        }
    }
}