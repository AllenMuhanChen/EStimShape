package org.xper.allen.drawing.composition;

public class TerminationData {
    int compId;
    AngularCoordinates angularPosition;
    double radialPosition;
    AngularCoordinates direction;
    double radius;

    public TerminationData(AngularCoordinates angularPosition, double radialPosition, AngularCoordinates direction, double radius) {
        this.angularPosition = angularPosition;
        this.radialPosition = radialPosition;
        this.direction = direction;
        this.radius = radius;
    }

    public TerminationData(int compId, AngularCoordinates angularPosition, double radialPosition, AngularCoordinates direction, double radius) {
        this.compId = compId;
        this.angularPosition = angularPosition;
        this.radialPosition = radialPosition;
        this.direction = direction;
        this.radius = radius;
    }

    public TerminationData() {
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

    public AngularCoordinates getDirection() {
        return direction;
    }

    public void setDirection(AngularCoordinates direction) {
        this.direction = direction;
    }

    public double getRadius() {
        return radius;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }

    public int getCompId() {
        return compId;
    }

    public void setCompId(int compId) {
        this.compId = compId;
    }

    @Override
    public String toString() {
        return "TerminationData{" +
                "compId=" + compId +
                "angularPosition=" + angularPosition +
                ", radialPosition=" + radialPosition +
                ", direction=" + direction +
                ", radius=" + radius +
                '}';
    }
}