package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.SplineInterpolator;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.apache.commons.math3.analysis.UnivariateFunction;

import javax.vecmath.Point2d;
import java.util.List;

public class NaturalSpline implements UnivariateFunction{

    private UnivariateRealFunction splineFunction;

    public NaturalSpline(double[] controlPoints_x, double[] controlPoints_y) {
        createSpline(controlPoints_x, controlPoints_y);
    }

    public NaturalSpline(List<Point2d> controlPoints) {
        double[] controlPoints_x = new double[controlPoints.size()];
        double[] controlPoints_y = new double[controlPoints.size()];
        for (int i = 0; i < controlPoints.size(); i++) {
            controlPoints_x[i] = controlPoints.get(i).x;
            controlPoints_y[i] = controlPoints.get(i).y;
        }
        createSpline(controlPoints_x, controlPoints_y);
    }

    @Override
    public double value(double x) {
        try {
            return splineFunction.value(x);
        } catch (FunctionEvaluationException e) {
            throw new RuntimeException(e);
        }
    }


    private void createSpline(double[] x, double[] y){
        SplineInterpolator splineInterpolator = new SplineInterpolator();
        splineFunction = splineInterpolator.interpolate(x, y);
    }

}