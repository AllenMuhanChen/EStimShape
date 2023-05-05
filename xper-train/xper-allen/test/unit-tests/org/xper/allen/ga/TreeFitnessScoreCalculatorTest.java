package org.xper.allen.ga;

import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.apache.commons.math3.analysis.UnivariateFunction;
import org.junit.Before;
import org.junit.Test;
import org.xper.allen.ga3d.blockgen.NaturalSpline;

import javax.vecmath.Point2d;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

import static org.junit.Assert.*;

public class TreeFitnessScoreCalculatorTest {

    private TreeFitnessScoreCalculator treeFitnessScoreCalculator;

    @Before
    public void setUp() throws Exception {
        treeFitnessScoreCalculator = new TreeFitnessScoreCalculator();

        Map<Integer, UnivariateRealFunction> fitnessScoreFunctionsForCanopyWidthThresholds = new HashMap<>();
        NaturalSpline narrowCanopySpline_linear = new NaturalSpline(Arrays.asList(new Point2d(0, 0), new Point2d(0.5, 0.5), new Point2d(1, 1)));
        fitnessScoreFunctionsForCanopyWidthThresholds.put(0, narrowCanopySpline_linear);
        NaturalSpline wideCanopySpline_bell = new NaturalSpline(Arrays.asList(new Point2d(0, 0), new Point2d(0.5, 1), new Point2d(1, 0)));
        fitnessScoreFunctionsForCanopyWidthThresholds.put(4, wideCanopySpline_bell);

        treeFitnessScoreCalculator.setFitnessFunctionsForCanopyWidthThresholds(fitnessScoreFunctionsForCanopyWidthThresholds);

        treeFitnessScoreCalculator.setMaxResponseSource(new MaxResponseSource(){
            @Override
            public double getValue(String gaName) {
                return 1.0;
            }
        });
    }

    /**
     * We've defined a linear function for narrow canopies and a bell-shaped function for wide canopies.
     * We test that the correct function is chosen depending on the canopy width.
     * We also test that the correct fitness score is computed for each function.
     */
    @Test
    public void chooses_correct_fitness_score_function_and_computes_score_correctly() {
        TreeFitnessScoreParameters testParams_narrow_canopy = new TreeFitnessScoreParameters(0.5, 1);
        double actualScore = treeFitnessScoreCalculator.calculateFitnessScore(testParams_narrow_canopy);
        double expectedScore = 0.5;
        assertEquals(expectedScore, actualScore, 0.0001);

        TreeFitnessScoreParameters testParams_wide_canopy = new TreeFitnessScoreParameters(0.5, 5);
        actualScore = treeFitnessScoreCalculator.calculateFitnessScore(testParams_wide_canopy);
        expectedScore = 1;
        assertEquals(expectedScore, actualScore, 0.0001);
    }

    /**
     * We set max response to 2, so a spikerate of 1 should be normalized to 0.5.
     * This test uses the narrow canopy fitness score function, which is a linear function.
     * So If the normalized spike rate is 0.5, should give a fitness score of 0.5
     */
    @Test
    public void normalizes_spike_rates(){
        treeFitnessScoreCalculator.setMaxResponseSource(new MaxResponseSource(){
            @Override
            public double getValue(String gaName) {
                return 2.0;
            }
        });

        TreeFitnessScoreParameters testParams_narrow_canopy = new TreeFitnessScoreParameters(1.0, 1);
        double actualScore = treeFitnessScoreCalculator.calculateFitnessScore(testParams_narrow_canopy);
        double expectedScore = 0.5;
        assertEquals(expectedScore, actualScore, 0.0001);

    }


}