package org.xper.allen.drawing.composition.morph;

import java.util.*;
import java.util.concurrent.atomic.AtomicReference;

public class NormalMorphDistributer {

    private double sigma = 1.0/3.0;

    public NormalMorphDistributer(double sigma) {
        this.sigma = sigma;
    }

    public void distributeMagnitudeTo(Collection<AtomicReference<Double>> paramMagnitudes, double magnitude) {
        List<AtomicReference<Double>> magnitudesToDistributeTo = new LinkedList<>(paramMagnitudes);
        double amountLeftToDistribute = magnitude;
        double maxPerParam = 1.0 / paramMagnitudes.size();
        while (Math.round(amountLeftToDistribute*100000.0)/100000.0 > 0.0) {
            Collections.shuffle(magnitudesToDistributeTo);
            for (AtomicReference<Double> paramMagnitude : magnitudesToDistributeTo) {
                double randomMagnitude = randomTruncatedNormal(0.5, sigma, 0, 1) * maxPerParam;
                // If the random magnitude is greater than the amount left to distribute, set it to the amount left to distribute
                if (randomMagnitude > amountLeftToDistribute) {
                    randomMagnitude = amountLeftToDistribute;
                }
                // If adding the random magnitude to the current magnitude would exceed the max, set it to the amount that would bring the current magnitude to the max
                if (paramMagnitude.get() + randomMagnitude > maxPerParam) {
                    randomMagnitude = maxPerParam - paramMagnitude.get();
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