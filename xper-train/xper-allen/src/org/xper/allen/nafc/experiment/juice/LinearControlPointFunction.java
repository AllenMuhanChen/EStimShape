package org.xper.allen.nafc.experiment.juice;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.xper.Dependency;

import java.util.List;

public class LinearControlPointFunction implements UnivariateRealFunction {
    @Dependency
    private List<Double> xValues;

    @Dependency
    private List<Double> yValues;

    public LinearControlPointFunction() {
    }

    @Override
    public double value(double v) throws FunctionEvaluationException {
        if (xValues.size() != yValues.size()) {
            throw new IllegalArgumentException("X and Y lists must be of the same size");
        }
        if (v < xValues.get(0) || v > xValues.get(xValues.size() - 1)) {
            throw new FunctionEvaluationException(v, "Input value is out of the xValues range");
        }

        // Find the interval v is in
        int i = 0;
        while (i < xValues.size() - 1 && v > xValues.get(i + 1)) {
            i++;
        }

        // Linear interpolation formula: y = y1 + (y2 - y1) * (v - x1) / (x2 - x1)
        double x1 = xValues.get(i);
        double y1 = yValues.get(i);
        double x2 = xValues.get(i + 1);
        double y2 = yValues.get(i + 1);

        return y1 + (y2 - y1) * (v - x1) / (x2 - x1);
    }

    public List<Double> getxValues() {
        return xValues;
    }

    public void setxValues(List<Double> xValues) {
        this.xValues = xValues;
    }

    public List<Double> getyValues() {
        return yValues;
    }

    public void setyValues(List<Double> yValues) {
        this.yValues = yValues;
    }
}