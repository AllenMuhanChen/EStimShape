package org.xper.allen.drawing.composition.morph;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class ValueShifter1D {
    private double MIN_VALUE;
    private double MAX_VALUE;

    public ValueShifter1D(double MIN_VALUE, double MAX_VALUE) {
        this.MIN_VALUE = MIN_VALUE;
        this.MAX_VALUE = MAX_VALUE;
    }

    /**
     * @param magnitude - number between 0 and 1. One represents a shift to the furthest point away
     *                  from the old value. Zero represents no shift. Numbers in between
     *                  represent a percentage of the maximum possible shift
     * @param oldValue - the value to be shifted
     * @return
     */
    public Double convert(Double magnitude, Double oldValue) {
        double distToMin = Math.abs(oldValue - MIN_VALUE);
        double distToMax = Math.abs(oldValue - MAX_VALUE);
        double maxDist = Math.max(distToMin, distToMax);

        double normalizedDistToMin = distToMin / maxDist;
        double normalizedDistToMax = distToMax / maxDist;

        List<Double> possibleLengths = new ArrayList<Double>();
        if (normalizedDistToMin >= magnitude)
            possibleLengths.add(oldValue - magnitude * maxDist);
        if (normalizedDistToMax >= magnitude)
            possibleLengths.add(oldValue + magnitude * maxDist);


        Collections.shuffle(possibleLengths);
        return possibleLengths.get(0);
    }
}