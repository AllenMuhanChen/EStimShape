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

    public AngularCoordinates(AngularCoordinates other) {
        this.theta = other.theta;
        this.phi = other.phi;
    }

    @Override
    public String toString() {
        return "AngularCoordinates{" +
                "theta=" + theta +
                ", phi=" + phi +
                '}';
    }
}