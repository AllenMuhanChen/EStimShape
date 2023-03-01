package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.FunctionEvaluationException;
import org.junit.Before;
import org.junit.Test;
import org.knowm.xchart.SwingWrapper;
import org.knowm.xchart.XYChart;
import org.knowm.xchart.XYSeries;
import org.knowm.xchart.internal.series.Series;
import org.knowm.xchart.style.Styler;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point2d;
import java.util.LinkedList;

import static org.junit.Assert.assertEquals;

public class SplineTest {

    @Before
    public void setUp() throws Exception {
    }

    @Test
    public void test_line() throws FunctionEvaluationException {
        LinkedList<Point2d> controlPoints = new LinkedList<Point2d>();
        controlPoints.add(new Point2d(0, 0));
        controlPoints.add(new Point2d(1, 1));
        controlPoints.add(new Point2d(2, 2));
        Spline spline = new Spline(controlPoints);

        double test_x = 0.5;
        double actual_y = spline.getValue(test_x);
        double expected_y = 0.5;

        assertEquals(expected_y, actual_y, 0.0001);
    }

    @Test
    public void test_curved() throws FunctionEvaluationException {
        LinkedList<Point2d> controlPoints = new LinkedList<Point2d>();
        controlPoints.add(new Point2d(0, 0));
        controlPoints.add(new Point2d(1, 1));
        controlPoints.add(new Point2d(2, 4));
        Spline spline = new Spline(controlPoints);

        double test_x = 0.5;
        double actual_y = spline.getValue(test_x);
        double expected_y = 0.3125;

        assertEquals(expected_y, actual_y, 0.0001);

        plotSpline(spline);
    }

    private void plotSpline(Spline spline) throws FunctionEvaluationException {
        XYChart chart = new XYChart(800, 600);
        chart.setTitle("Spline Test");
        chart.getStyler().setLegendPosition(Styler.LegendPosition.InsideNW);

        double begin = 0.0;
        double end = 2.0;
        int numPoints = 100;
        double[] x = new double[numPoints];
        double[] y = new double[numPoints];
        int index = 0;
        for (double i = begin; i <= end; i += (end - begin) / numPoints) {
            x[index] = i;
            y[index] = spline.getValue(i);
            index++;
        }
        XYSeries splineSeries = chart.addSeries("Spline", x, y);

        // Show the chart
        new SwingWrapper<>(chart).displayChart();

        ThreadUtil.sleep(100000);
    }
}