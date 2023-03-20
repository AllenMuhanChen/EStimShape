package org.xper.allen.drawing.composition.morph;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class LengthMorpher {

    private static final Double MIN_LENGTH = 1.5;
    private static final double RADIUS_VIEW = 5.0;
    private double MAX_LENGTH;

    public Double morphLength(Double oldLength, Double curvatureRadius, Double lengthMagnitude) {
        // Max length is a quarter turn of the curvature, but if there's no curvature, it's the radius of the view
        MAX_LENGTH = Math.min(curvatureRadius * Math.PI, RADIUS_VIEW);

        double distToMin = Math.abs(oldLength - MIN_LENGTH);
        double distToMax = Math.abs(oldLength - MAX_LENGTH);
        double maxDist = Math.max(distToMin, distToMax);

        double normalizedDistToMin = distToMin / maxDist;
        double normalizedDistToMax = distToMax / maxDist;

        List<Double> possibleLengths = new ArrayList<>();
        if (normalizedDistToMin >= lengthMagnitude)
            possibleLengths.add(oldLength - lengthMagnitude*(oldLength-MIN_LENGTH));
        if (normalizedDistToMax >= lengthMagnitude)
            possibleLengths.add(oldLength + lengthMagnitude*(MAX_LENGTH-oldLength));

        Collections.shuffle(possibleLengths);
        return possibleLengths.get(0);
    }
}