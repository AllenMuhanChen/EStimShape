package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.apache.commons.math3.analysis.UnivariateFunction;
import javax.vecmath.Point2d;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.List;

public class LinearSpline implements UnivariateRealFunction {

    private List<Point2d> controlPoints;

    public LinearSpline(List<Point2d> controlPoints) {
        this.controlPoints = new ArrayList<Point2d>(controlPoints);
        Collections.sort(this.controlPoints, new Comparator<Point2d>() {
            @Override
            public int compare(Point2d p1, Point2d p2) {
                return Double.compare(p1.getX(), p2.getX());
            }
        });
    }

    @Override
    public double value(double x) {
        Point2d lowerBound = null;
        Point2d upperBound = null;

        for (int i = 0; i < controlPoints.size(); i++) {
            Point2d currentPoint = controlPoints.get(i);
            if (currentPoint.getX() < x) {
                lowerBound = currentPoint;
            } else if (currentPoint.getX() == x) {
                if (i < controlPoints.size() - 1 && controlPoints.get(i + 1).getX() == x) {
                    return Math.max(currentPoint.getY(), controlPoints.get(i + 1).getY());
                } else {
                    return currentPoint.getY();
                }
            } else {
                upperBound = currentPoint;
                break;
            }
        }

        if (lowerBound == null || upperBound == null) {
            return 0;
        }

        double slope = (upperBound.getY() - lowerBound.getY()) / (upperBound.getX() - lowerBound.getX());
        double y = lowerBound.getY() + slope * (x - lowerBound.getX());

        return y;
    }
}