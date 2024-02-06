package org.xper.allen.drawing.ga;

import javax.vecmath.Point2d;

public abstract class ReceptiveField {
    public abstract boolean isInRF(double x, double y);
    public boolean isInRF(Point2d p){
        return isInRF(p.x, p.y);
    }
}