package org.xper.allen.drawing.composition.morph;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public class NormalMorphDistributer {

    private final double discreteness;

    /**
     *
     * @param discreteness: number between 0 (exclusive) and 1 (inclusive). The lower the discreteness, the more likely the distribution will be uniform.
     *                      The higher the discreteness, the more likely the distribution will be skewed towards high values in small numbers of parameters.
     */
    public NormalMorphDistributer(double discreteness) {
        this.discreteness = discreteness;
    }

    public void distributeMagnitudeTo(Collection<AtomicReference<Double>> paramMagnitudes, double magnitude) {
        List<AtomicReference<Double>> magnitudesToDistributeTo = new LinkedList<>(paramMagnitudes);
        double amountLeftToDistribute = magnitude;
        int numParams = magnitudesToDistributeTo.size();
        double maxPerParam = 1.0 / numParams;
        double buffer = 0.1 * maxPerParam; // magnitude being 1.0 may lead to impossible configurations, so we'd like to avoid this.
        while (Math.round(amountLeftToDistribute*100000.0)/100000.0 > 0.0) {
            Collections.shuffle(magnitudesToDistributeTo);
            for (AtomicReference<Double> paramMagnitude : magnitudesToDistributeTo) {
                double mean = (maxPerParam - buffer) * discreteness;
                double randomMagnitude = randomTruncatedNormal(mean, (maxPerParam-mean)/3, 0, maxPerParam- buffer);
                // If the random magnitude is greater than the amount left to distribute, set it to the amount left to distribute
                if (randomMagnitude > amountLeftToDistribute) {
                    randomMagnitude = amountLeftToDistribute;
                }
                // If adding the random magnitude to the current magnitude would exceed the max, set it to the amount that would bring the current magnitude to the max
                if (paramMagnitude.get() + randomMagnitude > maxPerParam-buffer) {
                    randomMagnitude = (maxPerParam-buffer) - paramMagnitude.get();
                }

                paramMagnitude.set(paramMagnitude.get() + randomMagnitude);
                amountLeftToDistribute -= randomMagnitude;
            }
        }

        // Normalize the magnitudes
        for (AtomicReference<Double> paramMagnitude : paramMagnitudes) {
            paramMagnitude.set(paramMagnitude.get() / maxPerParam);
        }
    }

    private double randomTruncatedNormal(double mean, double stdDev, double min, double max) {
        Random random = new Random();
        double randomValue = random.nextGaussian() * stdDev + mean;
        while (randomValue < min || randomValue > max) {
            randomValue = random.nextGaussian() * stdDev + mean;
        }
        return randomValue;
    }
}