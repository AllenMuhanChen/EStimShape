package org.xper.allen.ga3d.blockgen;

import org.apache.commons.math.FunctionEvaluationException;
import org.apache.commons.math.analysis.UnivariateRealFunction;
import org.junit.Before;
import org.junit.Test;
import org.knowm.xchart.SwingWrapper;
import org.knowm.xchart.XYChart;
import org.knowm.xchart.XYSeries;
import org.knowm.xchart.style.Styler;
import org.xper.allen.config.NewGAConfig;
import org.xper.allen.ga.regimescore.Regime;
import org.xper.util.ThreadUtil;

import javax.vecmath.Point2d;
import java.util.LinkedList;
import java.util.Map;

import static org.junit.Assert.assertEquals;

public class FunctionTest {

    private NewGAConfig config;

    @Before
    public void setUp() throws Exception {
        config = new NewGAConfig();
    }



    @Test
    public void test_peak_to_slope() throws FunctionEvaluationException {
        LinkedList<Point2d> peakPoints = new LinkedList<Point2d>();
        peakPoints.add(new Point2d(0, 0));
        peakPoints.add(new Point2d(0.5, 1));
        peakPoints.add(new Point2d(1, 0));

        LinkedList<Point2d> slopePoints = new LinkedList<Point2d>();
        slopePoints.add(new Point2d(0, 0));
        slopePoints.add(new Point2d(0.5, 0.9));
        slopePoints.add(new Point2d(0.75, 0.99));
        slopePoints.add(new Point2d(1, 1));

        NaturalSpline peakSpline = new NaturalSpline(peakPoints);
        NaturalSpline slopeSpline = new NaturalSpline(slopePoints);

        XYChart chart = initChart();
        addFunctionToChart(peakSpline, chart, "Peak", 0.0, 1.0);
        addFunctionToChart(slopeSpline, chart, "Slope", 0.0, 1.0);
        show(chart);
    }

    @Test
    public void test_slot_function_for_lineage() throws FunctionEvaluationException {
        UnivariateRealFunction function = config.slotFunctionForLineage();
        System.out.println(function.value(4.0));
        plotFunction(function, "SLot Function For Lineage", 0.0, 4.0);
    }

    @Test
    public void test_slot_functions_for_regimes() throws FunctionEvaluationException {
        XYChart chart = initChart();
        Map<Regime, UnivariateRealFunction> slotFunctions = config.slotFunctionForRegimes();
        for (Regime regime : slotFunctions.keySet()) {
            UnivariateRealFunction function = slotFunctions.get(regime);
            addFunctionToChart(function,chart,  "Slot Function For Regime " + regime, 0.0, 4.0);
        }
        show(chart);
    }


    @Test
    public void test_regime_one_sigmoid() throws FunctionEvaluationException {
        UnivariateRealFunction spline = config.fitnessFunctionForRegimeOne();
        plotFunction(spline, "Regime One Sigmoid", 0.0, 1.0);
    }

    @Test
    public void test_regime_two_sigmoid() throws FunctionEvaluationException {
        UnivariateRealFunction spline = config.fitnessFunctionForRegimeTwo();


        plotFunction(spline, "Regime Two Sigmoid", 0.0, 1.0);
    }

    @Test
    public void test_regime_three_step() throws FunctionEvaluationException {
        UnivariateRealFunction function = config.fitnessFunctionForRegimeThree();


        plotFunction(function, "Regime Three Step Function", 0.0, 1.0);
    }

    public static XYChart plotFunction(UnivariateRealFunction function, String title, double begin, double end) throws FunctionEvaluationException {
        XYChart chart = initChart();
        addFunctionToChart(function, chart, title, begin, end);
        show(chart);
        return chart;
    }

    private static void show(XYChart chart) {
        // Show the chart
        new SwingWrapper<>(chart).displayChart();
        ThreadUtil.sleep(100000);
    }

    private static void addFunctionToChart(UnivariateRealFunction function, XYChart chart, String seriesName, double begin, double end) throws FunctionEvaluationException {
        int numPoints = 100;
        double[] x = new double[numPoints];
        double[] y = new double[numPoints];
        int index = 0;
        for (double i = begin; i <= end; i += (end - begin) / numPoints) {
            x[index] = i;
            y[index] = function.value(i);
            index++;
        }
        XYSeries splineSeries = chart.addSeries(seriesName, x, y);
    }

    private static XYChart initChart() {
        XYChart chart = new XYChart(800, 600);
        chart.setTitle("Function Test");
        chart.getStyler().setLegendPosition(Styler.LegendPosition.InsideNW);

        return chart;
    }

}