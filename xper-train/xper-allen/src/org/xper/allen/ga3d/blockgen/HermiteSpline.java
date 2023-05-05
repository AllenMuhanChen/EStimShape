package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.apache.commons.math3.analysis.interpolation.HermiteInterpolator;

import javax.vecmath.Point2d;
import java.util.List;

public class HermiteSpline implements UnivariateRealFunction {

    private HermiteInterpolator hermiteInterpolator;

    public HermiteSpline(List<ControlPoint> controlPoints) {
        hermiteInterpolator = new HermiteInterpolator();


        for (int i=0; i<controlPoints.size(); i++) {
            double[] values = new double[controlPoints.get(i).derivatives.length + 1];
            double x = controlPoints.get(i).x;
            values[0] = controlPoints.get(i).y;
            for (int j=0; j<controlPoints.get(i).derivatives.length; j++) {
                values[j+1] = controlPoints.get(i).derivatives[j];
            }

            hermiteInterpolator.addSamplePoint(x, values);
        }
    }

    @Override
    public double value(double v) throws FunctionEvaluationException {
        // Use index 0, for the value, index 1 for first derivative, and so on.
        return hermiteInterpolator.value(v)[0];
    }

    public static class ControlPoint{
        public double x;
        public double y;
        public double[] derivatives;

        public ControlPoint(double x, double y, double[] derivatives){
            this.x = x;
            this.y = y;
            this.derivatives = derivatives;
        }

    }
}