package org.xper.allen.drawing.composition.morph;

public class LengthMorpher {

    private static final Double MIN_LENGTH = 2.0;
    private static final double RADIUS_VIEW = 5.0;
    private double MAX_LENGTH;

    public Double morphLength(Double oldLength, Double curvatureRadius, Double lengthMagnitude) {
        // Max length is a quarter turn of the curvature, but if there's no curvature, it's the radius of the view
        MAX_LENGTH = Math.min(curvatureRadius * Math.PI, RADIUS_VIEW);
        ValueShifter1D converter = new ValueShifter1D(MIN_LENGTH, MAX_LENGTH);
        return converter.convert(lengthMagnitude, oldLength);
    }

}