package org.xper.allen.drawing.ga;

import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point2d;

public abstract class ReceptiveField {
    public Coordinates2D center;
    public abstract boolean isInRF(double x, double y);
    public boolean isInRF(Point2d p){
        return isInRF(p.x, p.y);
    }
}