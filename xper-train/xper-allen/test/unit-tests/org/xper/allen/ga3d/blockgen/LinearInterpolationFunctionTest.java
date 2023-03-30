package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.apache.commons.math3.analysis.UnivariateFunction;
import org.junit.Before;
import org.junit.Test;
import javax.vecmath.Point2d;

import java.util.Arrays;
import java.util.List;

import static org.junit.Assert.*;

public class LinearInterpolationFunctionTest {

    @Before
    public void setUp() throws Exception {
    }

    @Test
    public void testLinearInterpolation() throws FunctionEvaluationException {
        List<Point2d> controlPoints = Arrays.asList(
                new Point2d(0, 0),
                new Point2d(1, 0),
                new Point2d(2, 1),
                new Point2d(3, 4)
        );

        UnivariateRealFunction interpolationFunction = new LinearSpline(controlPoints);

        double x1 = 0.5;
        double y1 = interpolationFunction.value(x1);
        double expectedY1 = 0.0;
        assertEquals("Interpolation at x = " + x1, expectedY1, y1, 1e-9);

        double x2 = 1.5;
        double y2 = interpolationFunction.value(x2);
        double expectedY2 = 0.5;
        assertEquals("Interpolation at x = " + x2, expectedY2, y2, 1e-9);

        double x3 = 2.5;
        double y3 = interpolationFunction.value(x3);
        double expectedY3 = 2.5;
        assertEquals("Interpolation at x = " + x3, expectedY3, y3, 1e-9);
    }
}