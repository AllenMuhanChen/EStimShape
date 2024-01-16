package org.xper.allen.drawing.composition;

import java.util.LinkedList;
import java.util.List;

public class JunctionData {
    AngularCoordinates angularPosition;
    double radialPosition;
    List<AngularCoordinates> angleBisectorDirection;
    double radius;
    LinkedList<Double> angularSubtense;
    List<Double> planarRotation;

    public JunctionData(AngularCoordinates angularPosition, double radialPosition, LinkedList<AngularCoordinates> angleBisectorDirection, double radius, LinkedList<Double> angularSubtense, List<Double> planarRotation) {
        this.angularPosition = angularPosition;
        this.radialPosition = radialPosition;
        this.angleBisectorDirection = angleBisectorDirection;
        this.radius = radius;
        this.angularSubtense = angularSubtense;
        this.planarRotation = planarRotation;
    }

    public JunctionData() {
    }

    public AngularCoordinates getAngularPosition() {
        return angularPosition;
    }

    public void setAngularPosition(AngularCoordinates angularPosition) {
        this.angularPosition = angularPosition;
    }

    public double getRadialPosition() {
        return radialPosition;
    }

    public void setRadialPosition(double radialPosition) {
        this.radialPosition = radialPosition;
    }

    public List<AngularCoordinates> getAngleBisectorDirection() {
        return angleBisectorDirection;
    }

    public void setAngleBisectorDirection(LinkedList<AngularCoordinates> angleBisectorDirection) {
        this.angleBisectorDirection = angleBisectorDirection;
    }

    public double getRadius() {
        return radius;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }

    public LinkedList<Double> getAngularSubtense() {
        return angularSubtense;
    }

    public void setAngularSubtense(LinkedList<Double> angularSubtense) {
        this.angularSubtense = angularSubtense;
    }

    public List<Double> getPlanarRotation() {
        return planarRotation;
    }

    public void setPlanarRotation(List<Double> planarRotation) {
        this.planarRotation = planarRotation;
    }

    @Override
    public String toString() {
        return "JunctionData{" +
                "angularPosition=" + angularPosition +
                ", radialPosition=" + radialPosition +
                ", angleBisectorDirection=" + angleBisectorDirection +
                ", radius=" + radius +
                ", angularSubtense=" + angularSubtense +
                ", planarRotation=" + planarRotation +
                '}';
    }
}