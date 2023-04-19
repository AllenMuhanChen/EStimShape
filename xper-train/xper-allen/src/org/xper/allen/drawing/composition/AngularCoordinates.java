package org.xper.allen.drawing.composition;

public class AngularCoordinates {
    public double theta;
    public double phi;

    public AngularCoordinates() {
    }

    public AngularCoordinates(double theta, double phi) {
        this.theta = theta;
        this.phi = phi;
    }

    @Override
    public String toString() {
        return "AngularCoordinates{" +
                "theta=" + theta +
                ", phi=" + phi +
                '}';
    }
}