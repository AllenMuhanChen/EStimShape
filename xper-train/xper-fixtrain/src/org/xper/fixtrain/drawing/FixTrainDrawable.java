package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

public abstract class FixTrainDrawable {
    protected Coordinates2D fixationPosition;
    public abstract void draw(Context context);
    public abstract void setSpec (String spec);

    public Coordinates2D getFixationPosition() {
        return fixationPosition;
    }

    public void setFixationPosition(Coordinates2D fixationPosition) {
        this.fixationPosition = fixationPosition;
    }

    public abstract String getSpec();
}