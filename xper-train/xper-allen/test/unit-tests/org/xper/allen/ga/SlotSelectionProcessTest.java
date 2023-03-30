package org.xper.allen.ga;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.allen.ga.regimescore.RegimeScoreSource;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.*;

import static org.junit.Assert.assertEquals;

public class SlotSelectionProcessTest {

    private SlotSelectionProcess slotSelectionProcess;

    @Before
    public void setUp() throws Exception {
        slotSelectionProcess = new SlotSelectionProcess();

        slotSelectionProcess.setDbUtil(new MockDbUtil());
        slotSelectionProcess.setNumChildrenToSelect(10000);
        slotSelectionProcess.setRegimeScoreSource(new MockRegimeScoreSource());
        slotSelectionProcess.setSlotFunctionForLineage(slotFunctionForLineage());
        slotSelectionProcess.setSlotFunctionForRegimes(slotFunctionForRegimes());
        slotSelectionProcess.setFitnessFunctionForRegimes(mockFitnessFunction());
        slotSelectionProcess.setSpikeRateSource(new MockSpikeRateSource());
    }

    @Test
    public void selects_appropiate_number_and_ratios_of_slots() {
        List<Child> children = slotSelectionProcess.select("SlotSelectionProcessTest");

        assertEquals(10000, children.size());
        correct_proportion_of_slots_to_lineages(children);
        correct_proportion_of_slots_to_regimes(children);
    }

    /**
     * Lineage 2 should have roughly twice the amount of slots as lineage 1.
     * @param children
     */
    private void correct_proportion_of_slots_to_lineages(List<Child> children) {
        int lineage1Count = 0;
        int lineage2Count = 0;
        for (Child child : children) {
            if (child.getParentId() == 11L || child.getParentId() == 12L) {
                lineage1Count++;
            } else if (child.getParentId() == 21L || child.getParentId() == 22L) {
                lineage2Count++;
            }
        }
        assertEquals(1/3 * 10000, lineage1Count/lineage2Count, 100);
    }

    /**
     * Regime 2 should have roughly twice the amount of slots as regime 1
     * @param children
     */
    private void correct_proportion_of_slots_to_regimes(List<Child> children) {
        int regime1Count = 0;
        int regime2Count = 0;
        for (Child child : children) {
            if (child.getRegime() == Regime.ONE) {
                regime1Count++;
            } else if (child.getRegime() == Regime.TWO) {
                regime2Count++;
            }
        }
        assertEquals(1/3*10000, regime1Count/regime2Count, 100);

    }

    /**
     * Lineages should have numbers of slots proportional to their regime score.
     */
    private UnivariateRealFunction slotFunctionForLineage() {
        return new UnivariateRealFunction() {
            @Override
            public double value(double regimeScore) throws FunctionEvaluationException {
                return regimeScore;
            }
        };
    }

    /**
     * For simplicity, we have only two regimes.
     * Regime One is the only option when regime score is one
     * Regime Two is the only option when regime score is two
     */
    private Map<Regime, UnivariateRealFunction> slotFunctionForRegimes() {
        Map<Regime, UnivariateRealFunction> output = new LinkedHashMap<>();

        output.put(Regime.ONE, x->{
            if (x==1){
                return 1;
            } else {
                return 0;
            }
        });
        output.put(Regime.TWO, x->{
            if (x==2){
                return 1;
            } else {
                return 0;
            }
        });

        return output;
    }

    /**
     * Regimes should have numbers of slots proportional to their regime score.
     */
    private UnivariateRealFunction regimeSlotFunction() {
        return new UnivariateRealFunction() {
            @Override
            public double value(double regimeScore) throws FunctionEvaluationException {
                return regimeScore;
            }
        };
    }

    /**
     * For simplicity, we have only two regimes. Have the fitness function be the same for both, which is just the same as the spikeRate
     * @return
     */
    private Map<Regime, UnivariateRealFunction> mockFitnessFunction() {
        Map<Regime, UnivariateRealFunction> output = new LinkedHashMap<>();

        output.put(Regime.ONE, new UnivariateRealFunction() {
            @Override
            public double value(double spikeRate) throws FunctionEvaluationException {
                return spikeRate;
            }
        });
        output.put(Regime.TWO, new UnivariateRealFunction() {
            @Override
            public double value(double spikeRate) throws FunctionEvaluationException {
                return spikeRate;
            }
        });

        return output;
    }



    private static class MockDbUtil extends MultiGaDbUtil {
        @Override
        public List<String> readAllTreeSpecsForGa(String gaName) {
            List<String> founders = new LinkedList<>();

            founders.add(new Branch<Long>(1L).toXml());
            founders.add(new Branch<Long>(2L).toXml());

            return founders;
        }

        @Override
        public List<Long> readStimIdsFromLineage(String gaName, Long lineageId) {
            // Give different stim Ids for each founder
            List<Long> stimIds = new LinkedList<>();
            if (lineageId == 1L) {
                stimIds.add(11L);
                stimIds.add(12L);
            } else {
                stimIds.add(21L);
                stimIds.add(22L);
            }
            return stimIds;
        }
    }

    private static class MockRegimeScoreSource extends RegimeScoreSource {
        @Override
        public Double getLineageScore(Long lineageId) {
            // Give different regime score to different lineages
            if (lineageId == 1L) {
                return 1.0;
            } else {
                return 2.0;
            }
        }
    }

    private static class MockSpikeRateSource implements SpikeRateSource {
        @Override
        public Double getSpikeRate(Long stimId) {
            // give default firing rate that matches our fitness function
            return 1.0;
        }
    }
}