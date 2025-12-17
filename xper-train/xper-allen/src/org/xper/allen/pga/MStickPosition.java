package org.xper.allen.pga;

import org.xper.allen.drawing.composition.experiment.PositioningStrategy;

import javax.vecmath.Point3d;

public class MStickPosition {
    PositioningStrategy positioningStrategy;
    Integer targetComp;
    Point3d position;


    public MStickPosition(PositioningStrategy positioningStrategy, Point3d position) {
        this.positioningStrategy = positioningStrategy;
        this.position = position;
        targetComp = null;
    }

    public MStickPosition(PositioningStrategy positioningStrategy, Integer targetComp, Point3d position) {
        this.positioningStrategy = positioningStrategy;
        this.targetComp = targetComp;
        this.position = position;
    }

    public PositioningStrategy getPositioningStrategy() {
        return positioningStrategy;
    }

    public void setPositioningStrategy(PositioningStrategy positioningStrategy) {
        this.positioningStrategy = positioningStrategy;
    }

    public Point3d getPosition() {
        return position;
    }

    public void setPosition(Point3d position) {
        this.position = position;
    }

    public Integer getTargetComp() {
        return targetComp;
    }

    public void setTargetComp(Integer targetComp) {
        this.targetComp = targetComp;
    }
}
