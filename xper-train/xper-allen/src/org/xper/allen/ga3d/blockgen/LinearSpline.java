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

        for (Point2d point : controlPoints) {
            if (point.getX() <= x) {
                lowerBound = point;
            } else {
                upperBound = point;
                break;
            }
        }

        if (lowerBound == null || upperBound == null) {
            throw new IllegalArgumentException("x is out of the control points range.");
        }

        double slope = (upperBound.getY() - lowerBound.getY()) / (upperBound.getX() - lowerBound.getX());
        double y = lowerBound.getY() + slope * (x - lowerBound.getX());

        return y;
    }
}