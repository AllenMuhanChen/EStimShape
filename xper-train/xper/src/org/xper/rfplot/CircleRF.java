package org.xper.rfplot;

import org.xper.drawing.Coordinates2D;

import java.util.LinkedList;
import java.util.List;

public class CircleRF {
    //Fields for rf circle
    private Coordinates2D circleCenter;
    private double circleRadius;
    private List<Coordinates2D> circlePoints = new LinkedList<>();

    public Coordinates2D getCircleCenter() {
        return circleCenter;
    }

    public void setCircleCenter(Coordinates2D circleCenter) {
        this.circleCenter = circleCenter;
    }

    public double getCircleRadius() {
        return circleRadius;
    }

    public void setCircleRadius(double circleRadius) {
        this.circleRadius = circleRadius;
    }

    public List<Coordinates2D> getCirclePoints() {
        return circlePoints;
    }

    public void setCirclePoints(List<Coordinates2D> circlePoints) {
        this.circlePoints = circlePoints;
    }

    public void addCirclePoint(Coordinates2D point) {
        circlePoints.add(point);
    }
}