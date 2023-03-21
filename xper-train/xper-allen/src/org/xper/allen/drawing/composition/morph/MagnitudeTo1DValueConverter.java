package org.xper.allen.drawing.composition.morph;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class MagnitudeTo1DValueConverter {
    private double MIN_VALUE;
    private double MAX_VALUE;

    public MagnitudeTo1DValueConverter(double MIN_VALUE, double MAX_VALUE) {
        this.MIN_VALUE = MIN_VALUE;
        this.MAX_VALUE = MAX_VALUE;
    }

    /**
     *
     * @param magnitude
     * @param oldValue
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
            possibleLengths.add(oldValue - magnitude * (oldValue - MIN_VALUE));
        if (normalizedDistToMax >= magnitude)
            possibleLengths.add(oldValue + magnitude * (MAX_VALUE - oldValue));

        Collections.shuffle(possibleLengths);
        return possibleLengths.get(0);
    }
}