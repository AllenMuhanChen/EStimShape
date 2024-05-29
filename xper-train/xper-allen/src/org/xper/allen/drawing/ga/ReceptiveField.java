package org.xper.allen.drawing.ga;

import org.xper.drawing.Coordinates2D;

import javax.vecmath.Point2d;
import java.util.LinkedList;
import java.util.List;

public abstract class ReceptiveField {
    public List<Coordinates2D> outline = new LinkedList<>(); //in mm
    public Coordinates2D center;
    public double radius;

    protected ReceptiveField() {
    }

    public abstract boolean isInRF(double x, double y);
    public boolean isInRF(Point2d p){
        return isInRF(p.x, p.y);
    }
    public List<Coordinates2D> getOutline(){
        return outline;
    }

    public Coordinates2D getCenter() {
        return center;
    }
}