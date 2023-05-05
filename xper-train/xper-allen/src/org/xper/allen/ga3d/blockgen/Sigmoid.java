package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.analysis.UnivariateRealFunction;

public class Sigmoid implements UnivariateRealFunction {

    private final double shift;
    private final double slope;

    public Sigmoid (double shift, double slope) {
        this.shift = shift;
        this.slope = slope;
    }

    @Override
    public double value(double x) {
        return 1.0 / (1.0 + Math.exp(-slope * (x - shift)));
    }


}