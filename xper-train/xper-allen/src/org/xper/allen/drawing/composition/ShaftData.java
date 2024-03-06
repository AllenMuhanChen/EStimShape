package org.xper.allen.drawing.composition;

import com.thoughtworks.xstream.annotations.XStreamAlias;

public class ShaftData {
    public AngularCoordinates angularPosition;
    public double radialPosition;
    public AngularCoordinates orientation;
    public double radius;
    public double length;
    public double curvature;


    public ShaftData() {
    }

    @Override
    public String toString() {
        return "ShaftData{" +
                "\n angularPosition=" + angularPosition +
                "\n radialPosition=" + radialPosition +
                "\n orientation=" + orientation +
                "\n radius=" + radius +
                "\n length=" + length +
                "\n curvature=" + curvature +
                '}';
    }
}