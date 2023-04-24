package org.xper.allen.ga;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;

import java.util.*;
import java.util.function.BiConsumer;

public class TreeFitnessScoreCalculator implements FitnessScoreCalculator<TreeFitnessScoreParameters>{

    @Dependency
    Map<Integer, UnivariateRealFunction> fitnessFunctionsForCanopyWidthThresholds; // (percentage_of_max_response, fitness_score)


    @Dependency
    MaxResponseSource maxResponseSource;

    /**
     * Chooses the proper fitness score function based on canopy width, normalizes the spike rate,
     * and then plugs the normalized spike rate through the chosen fitness function to get a fitness score.
     */
    @Override
    public double calculateFitnessScore(TreeFitnessScoreParameters params) {
        // Based on canopy width, define different fitnessScore functions between spike rate and fitness score.
        // Choose function associated with the greatest canopy width past threshold
        UnivariateRealFunction fitnessFunction = chooseFitnessFunctionBasedOnCanopyWidth(params);

        // Normalize spike rate by max response
        double normalizedSpikeRate = params.getAverageSpikeRate() / maxResponseSource.getValue(params.getGaName());

        // put spike rate through fitness score function associated with the canopy width
        try {
            return fitnessFunction.value(normalizedSpikeRate);
        } catch (FunctionEvaluationException e) {
            e.printStackTrace();
            System.err.println("Error evaluating fitness function for spike rate " + normalizedSpikeRate
                    + " and canopy width " + params.getCanopyWidth());
            System.err.println("Using fitness score of 0.0");
            return 0.0;
        }
    }

    private UnivariateRealFunction chooseFitnessFunctionBasedOnCanopyWidth(TreeFitnessScoreParameters params) {
        // Get all entries in fitnessFunctionsForCanopyWidthThresholds above canopy width
        List<Map.Entry<Integer, UnivariateRealFunction>> aboveThreshold = new LinkedList<>();
        fitnessFunctionsForCanopyWidthThresholds.forEach(new BiConsumer<Integer, UnivariateRealFunction>() {
            @Override
            public void accept(Integer threshold, UnivariateRealFunction fitnessFunction) {
                if (params.getCanopyWidth() > threshold) {
                    aboveThreshold.add(new AbstractMap.SimpleEntry<>(threshold, fitnessFunction));
                }
            }
        });

        // Find proper fitness function to use by getting highest-threshold entry in aboveThreshold
        aboveThreshold.sort(new Comparator<Map.Entry<Integer, UnivariateRealFunction>>() {
            /**
             * sorts from highest to lowest Canopy Width threshold values
             */
            @Override
            public int compare(Map.Entry<Integer, UnivariateRealFunction> o1, Map.Entry<Integer, UnivariateRealFunction> o2) {
                return o2.getKey() - o1.getKey();
            }
        });
        return aboveThreshold.get(0).getValue();
    }

    public Map<Integer, UnivariateRealFunction> getFitnessFunctionsForCanopyWidthThresholds() {
        return fitnessFunctionsForCanopyWidthThresholds;
    }

    public void setFitnessFunctionsForCanopyWidthThresholds(Map<Integer, UnivariateRealFunction> fitnessFunctionsForCanopyWidthThresholds) {
        this.fitnessFunctionsForCanopyWidthThresholds = fitnessFunctionsForCanopyWidthThresholds;
    }

    public MaxResponseSource getMaxResponseSource() {
        return maxResponseSource;
    }

    public void setMaxResponseSource(MaxResponseSource maxResponseSource) {
        this.maxResponseSource = maxResponseSource;
    }
}