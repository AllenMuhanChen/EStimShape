package org.xper.allen.ga;

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

        Map<Integer, UnivariateFunction> fitnessScoreFunctionsForCanopyWidths = new HashMap<>();
        fitnessScoreFunctionsForCanopyWidths.put(0, new NaturalSpline(Arrays.asList(new Point2d(0, 0), new Point2d(0.5, 0.5), new Point2d(1, 1))));
        fitnessScoreFunctionsForCanopyWidths.put(4, new NaturalSpline(Arrays.asList(new Point2d(0, 0), new Point2d(0.5, 1), new Point2d(1, 0))));

        treeFitnessScoreCalculator.setFitnessFunctionsForCanopyWidthThresholds(fitnessScoreFunctionsForCanopyWidths);
    }

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


}