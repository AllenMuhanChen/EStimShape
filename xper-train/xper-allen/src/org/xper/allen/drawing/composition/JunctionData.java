package org.xper.allen.drawing.composition;

import java.util.LinkedList;
import java.util.List;

public class JunctionData {
    AngularCoordinates angularPosition;
    double radialPosition;
    AngularCoordinates angleBisectorDirection;
    double radius;
    Double angularSubtense;
    Double planarRotation;
    List<Integer> connectedCompIds = new LinkedList<>();
    Integer id;

    public JunctionData(AngularCoordinates angularPosition, double radialPosition, AngularCoordinates angleBisectorDirection, double radius, Double angularSubtense, Double planarRotation) {
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

    public AngularCoordinates getAngleBisectorDirection() {
        return angleBisectorDirection;
    }

    public void setAngleBisectorDirection(AngularCoordinates angleBisectorDirection) {
        this.angleBisectorDirection = angleBisectorDirection;
    }

    public double getRadius() {
        return radius;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }

    public Double getAngularSubtense() {
        return angularSubtense;
    }

    public void setAngularSubtense(Double angularSubtense) {
        this.angularSubtense = angularSubtense;
    }

    public Double getPlanarRotation() {
        return planarRotation;
    }

    public void setPlanarRotation(Double planarRotation) {
        this.planarRotation = planarRotation;
    }

    public List<Integer> getConnectedCompIds() {
        return connectedCompIds;
    }

    public void setConnectedCompIds(List<Integer> connectedCompIds) {
        this.connectedCompIds = connectedCompIds;
    }

    public Integer getId() {
        return id;
    }

    public void setId(Integer id) {
        this.id = id;
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