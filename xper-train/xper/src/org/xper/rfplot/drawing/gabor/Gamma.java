package org.xper.rfplot.drawing.gabor;

public class Gamma {
    double A;
    double gamma;

    public Gamma(double a, double gamma) {
        A = a;
        this.gamma = gamma;
    }

    public double correct(double y) {
        return Math.pow(y / A, 1 / gamma);
    }

    public double getA() {
        return A;
    }

    public void setA(double a) {
        A = a;
    }

    public double getGamma() {
        return gamma;
    }

    public void setGamma(double gamma) {
        this.gamma = gamma;
    }
}