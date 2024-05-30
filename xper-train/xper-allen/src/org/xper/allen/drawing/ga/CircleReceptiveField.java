package org.xper.allen.drawing.ga;

import org.xper.drawing.Coordinates2D;

import java.util.ArrayList;
import java.util.List;

public class CircleReceptiveField extends ReceptiveField {

    private static final int DEFAULT_NUM_POINTS = 100; // Default number of points to define the circle

    public CircleReceptiveField(Coordinates2D center, double rfRadiusMm) {
        this.center = center;
        this.radius = rfRadiusMm;
        this.outline = calculateOutline(center, rfRadiusMm, DEFAULT_NUM_POINTS);
    }

    private List<Coordinates2D> calculateOutline(Coordinates2D center, double radius, int numPoints) {
        List<Coordinates2D> outlinePoints = new ArrayList<>();
        double angleIncrement = 2 * Math.PI / numPoints;

        for (int i = 0; i < numPoints; i++) {
            double angle = i * angleIncrement;
            double x = center.getX() + radius * Math.cos(angle);
            double y = center.getY() + radius * Math.sin(angle);
            outlinePoints.add(new Coordinates2D(x, y));
        }

        return outlinePoints;
    }

    @Override
    public boolean isInRF(double x, double y) {
        double distance = Math.sqrt(Math.pow(x - center.getX(), 2) + Math.pow(y - center.getY(), 2));
        return distance <= radius;
    }
}