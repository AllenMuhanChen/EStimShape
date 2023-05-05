package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.FunctionEvaluationException;
import org.junit.Test;
import org.xper.allen.ga3d.blockgen.HermiteSpline.ControlPoint;

import java.util.Arrays;
import java.util.List;

public class HermiteSplineTest {

    @Test
    public void value() throws FunctionEvaluationException {
        List<ControlPoint> controlPoints = Arrays.asList(
                new ControlPoint(0.0, 0.0, new double[]{0.5, -1.0}),
                new ControlPoint(0.5, 1, new double[]{0.0, -1.0}),
                new ControlPoint(1.0, 0.0, new double[]{0.5, 1.0})
        );

        HermiteSpline spline = new HermiteSpline(controlPoints);
        System.out.println(spline.value(1.0));

        FunctionTest.plotFunction(spline, "Spline", 0.0, 1.0);
    }
}