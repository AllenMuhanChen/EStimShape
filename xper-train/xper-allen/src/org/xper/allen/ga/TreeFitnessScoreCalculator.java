package org.xper.allen.ga;

import org.apache.commons.math3.analysis.UnivariateFunction;
import org.xper.Dependency;

import java.util.*;
import java.util.function.BiConsumer;

public class TreeFitnessScoreCalculator implements FitnessScoreCalculator<TreeFitnessScoreParameters>{

    @Dependency
    Map<Integer, UnivariateFunction> fitnessFunctionsForCanopyWidthThresholds; // (percentage_of_max_response, fitness_score)


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
        UnivariateFunction fitnessFunction = chooseFitnessFunctionBasedOnCanopyWidth(params);

        // Normalize spike rate by max response
        double normalizedSpikeRate = params.getAverageSpikeRate() / maxResponseSource.getMaxResponse(params.getGaName());

        // put spike rate through fitness score function associated with the canopy width
        return fitnessFunction.value(normalizedSpikeRate);
    }

    private UnivariateFunction chooseFitnessFunctionBasedOnCanopyWidth(TreeFitnessScoreParameters params) {
        // Get all entries in fitnessFunctionsForCanopyWidthThresholds above canopy width
        List<Map.Entry<Integer, UnivariateFunction>> aboveThreshold = new LinkedList<>();
        fitnessFunctionsForCanopyWidthThresholds.forEach(new BiConsumer<Integer, UnivariateFunction>() {
            @Override
            public void accept(Integer threshold, UnivariateFunction fitnessFunction) {
                if (params.getCanopyWidth() > threshold) {
                    aboveThreshold.add(new AbstractMap.SimpleEntry<>(threshold, fitnessFunction));
                }
            }
        });

        // Find proper fitness function to use by getting highest-threshold entry in aboveThreshold
        aboveThreshold.sort(new Comparator<Map.Entry<Integer, UnivariateFunction>>() {
            /**
             * sorts from highest to lowest Canopy Width threshold values
             */
            @Override
            public int compare(Map.Entry<Integer, UnivariateFunction> o1, Map.Entry<Integer, UnivariateFunction> o2) {
                return o2.getKey() - o1.getKey();
            }
        });
        return aboveThreshold.get(0).getValue();
    }

    public Map<Integer, UnivariateFunction> getFitnessFunctionsForCanopyWidthThresholds() {
        return fitnessFunctionsForCanopyWidthThresholds;
    }

    public void setFitnessFunctionsForCanopyWidthThresholds(Map<Integer, UnivariateFunction> fitnessFunctionsForCanopyWidthThresholds) {
        this.fitnessFunctionsForCanopyWidthThresholds = fitnessFunctionsForCanopyWidthThresholds;
    }

    public MaxResponseSource getMaxResponseSource() {
        return maxResponseSource;
    }

    public void setMaxResponseSource(MaxResponseSource maxResponseSource) {
        this.maxResponseSource = maxResponseSource;
    }
}