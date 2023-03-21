package org.xper.allen.drawing.composition.morph;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;

public class CurvatureMorpher {
    public final static double RADIUS_VIEW = 5.0;
    public final static double LOW_CURVATURE_UPPER = 1 / (6 * RADIUS_VIEW);
    public static final double MEDIUM_CURVATURE_LOWER = LOW_CURVATURE_UPPER;
    public static final double MEDIUM_CURVATURE_HIGHER = 1 / (0.6 * RADIUS_VIEW);
    public static final double HIGH_CURVATURE_LOWER = MEDIUM_CURVATURE_HIGHER;
    public static final double HIGH_CURVATURE_UPPER = 1 / (0.2 * RADIUS_VIEW);

    public Double morphCurvature(Double oldCurvature, Double curvatureMagnitude) {
        // Convert oldCurvature to a normalized curvature value
        double oldNormalizedCurvature;
        if (oldCurvature < LOW_CURVATURE_UPPER){
            oldNormalizedCurvature = 0;
        }
        else if (oldCurvature < MEDIUM_CURVATURE_HIGHER) {
            double normalizedMediumCurvature = (oldCurvature - MEDIUM_CURVATURE_LOWER) / (MEDIUM_CURVATURE_HIGHER - MEDIUM_CURVATURE_LOWER);
            oldNormalizedCurvature = 1.0/3.0 + normalizedMediumCurvature/3.0;
        }
        else if (oldCurvature <= HIGH_CURVATURE_UPPER) {
            double normalizedHighCurvature = (oldCurvature - HIGH_CURVATURE_LOWER) / (HIGH_CURVATURE_UPPER - HIGH_CURVATURE_LOWER);
            oldNormalizedCurvature = 2.0/3.0 + normalizedHighCurvature / 3.0;
        }
        else {
            throw new RuntimeException("Curvature value out of range: " + oldCurvature);
        }

        // Use curvature magnitude to determine the new normalized curvature value
        double MIN_CURVATURE = 0.0;
        double MAX_CURVATURE = 1.0;

        MagnitudeTo1DValueConverter converter = new MagnitudeTo1DValueConverter(MIN_CURVATURE, MAX_CURVATURE);
        double newNormalizedCurvature = converter.convert(curvatureMagnitude, oldNormalizedCurvature);

        // Convert the new normalized curvature value to a new curvature value
        if (newNormalizedCurvature <= 1.0/3.0) {
            return 1.0/10000;
        }
        else if (newNormalizedCurvature <= 2.0/3.0) {
            double normalizedMediumCurvature = (newNormalizedCurvature - 1.0/3.0) * 3.0;
            return MEDIUM_CURVATURE_LOWER + normalizedMediumCurvature * (MEDIUM_CURVATURE_HIGHER - MEDIUM_CURVATURE_LOWER);
        }
        else if (newNormalizedCurvature <= 1.0) {
            double normalizedHighCurvature = (newNormalizedCurvature - 2.0/3.0) * 3.0;
            return HIGH_CURVATURE_LOWER + normalizedHighCurvature * (HIGH_CURVATURE_UPPER - HIGH_CURVATURE_LOWER);
        }
        else{
            throw new RuntimeException("New normalized curvature value out of range: " + newNormalizedCurvature);
        }
    }
}