package org.xper.allen.ga;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.junit.Before;
import org.junit.Test;
import org.xper.allen.util.MultiGaDbUtil;

import java.util.*;

public class SlotSelectionProcessTest {

    private SlotSelectionProcess slotSelectionProcess;

    @Before
    public void setUp() throws Exception {
        slotSelectionProcess = new SlotSelectionProcess();

        slotSelectionProcess.setDbUtil(new MockDbUtil());
        slotSelectionProcess.setNumChildrenToSelect(10);
        slotSelectionProcess.setRegimeScoreSource(new MockRegimeScoreSource());

        slotSelectionProcess.setSlotFunctionForLineage(slotFunctionForLineage());
        slotSelectionProcess.setSlotFunctionForRegimes(slotFunctionForRegimes());
        slotSelectionProcess.setFitnessFunctionForRegimes(mockFitnessFunction());
        slotSelectionProcess.setSpikeRateSource(new MockSpikeRateSource());
    }

    @Test
    public void select() {
        List<Child> children = slotSelectionProcess.select("SlotSelectionProcessTest");

        System.out.println(children);

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
     */
    private Map<Regime, UnivariateRealFunction> slotFunctionForRegimes() {
        Map<Regime, UnivariateRealFunction> output = new LinkedHashMap<>();

        output.put(Regime.ONE, regimeSlotFunction());
        output.put(Regime.TWO, regimeSlotFunction());

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
        public List<Long> readStimIdsForLineage(String gaName, Long lineageId) {
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
        public Double getRegimeScore(Long lineageId) {
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
        public List<Double> getSpikeRates(Long taskId) {
            // give default firing rate that matches our fitness function
            return Collections.singletonList(1.0);
        }
    }
}