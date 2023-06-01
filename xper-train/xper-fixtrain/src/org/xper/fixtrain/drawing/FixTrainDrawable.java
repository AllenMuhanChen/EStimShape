package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

public abstract class FixTrainDrawable {
    protected Coordinates2D fixationPosition;
    public abstract void draw(Context context);
    public abstract void setSpec (String spec);

    /**
     * Updates the location of the fixation drawable, and updates
     * the drawable itself is the updateDrawable method is implemented.
     * @param fixationPosition
     */
    public void next(Coordinates2D fixationPosition){
        this.fixationPosition = fixationPosition;
        updateDrawable();
    }
    /**
     * Some drawables should be updated on every trial/calibration point.
     * This method is responsible for updating the drawable.
     */
    protected abstract void updateDrawable();

    public abstract String getSpec();
}