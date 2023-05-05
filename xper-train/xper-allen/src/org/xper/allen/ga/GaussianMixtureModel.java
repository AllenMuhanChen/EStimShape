package org.xper.allen.ga;

import org.apache.commons.math3.analysis.BivariateFunction;

import java.awt.geom.Point2D;
import java.util.ArrayList;
import java.util.List;

public class GaussianMixtureModel implements BivariateFunction {

    private List<GaussianParameter> parameters;

    public GaussianMixtureModel(List<GaussianParameter> parameters) {
        this.parameters = parameters;
    }

    public GaussianMixtureModel(List<Point2D> centers, List<Double> amplitudes, List<Double> sigmas) {
        if (centers.size() != amplitudes.size() || centers.size() != sigmas.size()) {
            throw new IllegalArgumentException("Input lists must have the same size.");
        }
        parameters = new ArrayList<>();
        for (int i = 0; i < centers.size(); i++) {
            parameters.add(new GaussianParameter(centers.get(i), amplitudes.get(i), sigmas.get(i)));
        }
    }

    @Override
    public double value(double x, double y) {
        double sum = 0;
        for (GaussianParameter parameter : parameters) {
            double dx = x - parameter.getCenter().getX();
            double dy = y - parameter.getCenter().getY();
            double mahalanobis = (dx * dx + dy * dy) / (parameter.getSigma() * parameter.getSigma());
            double factor = Math.exp(-0.5 * mahalanobis);
            double value = parameter.getAmplitude();
            sum += factor * value;
        }
        return sum;
    }
}


class GaussianParameter {
    private Point2D center;
    private double amplitude;
    private double sigma;

    public GaussianParameter(Point2D center, double amplitude, double sigma) {
        this.center = center;
        this.amplitude = amplitude;
        this.sigma = sigma;
    }

    public Point2D getCenter() {
        return center;
    }

    public double getAmplitude() {
        return amplitude;
    }

    public double getSigma() {
        return sigma;
    }
}