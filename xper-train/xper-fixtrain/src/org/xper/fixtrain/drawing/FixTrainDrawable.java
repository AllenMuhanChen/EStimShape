package org.xper.fixtrain.drawing;

import org.xper.drawing.Context;
import org.xper.drawing.Coordinates2D;

/**
 * Any drawable that is used in the fixation training task should extend this class.
 *
 * Specifies the required behavior:
 *
 * 1. The fixation position changes as calibration points
 * change
 * 2. The drawable's spec can auto-step as calibration points change
 * 2. We can manually change the drawable's spec
 * 3. We can scale the drawable's size without having outside knowledge of the spec
 *
 * and provides some default behavior.
 *
 *  You must define a type parameter for the size of the drawable. i.e, if it's a circle,
 *  the size type would be a double, for the diameter or radius of the circle. IF it's an image,
 *  The size type would a two dimensional object of some kind i.e Coordinates2D.
 *
 * Drawables
 * @param <SizeType>
 */
public abstract class FixTrainDrawable<SizeType> {
    protected Coordinates2D fixationPosition = new Coordinates2D(0,0);
    public abstract void draw(Context context);
    /**
     * Updates the location of the fixation drawable, and updates
     * the drawable itself is the updateDrawable method is implemented.
     * @param fixationPosition
     */
    public void next(Coordinates2D fixationPosition){
        nextFixationPosition(fixationPosition);
        nextDrawable();
    }

    private void nextFixationPosition(Coordinates2D fixationPosition) {
        this.fixationPosition = fixationPosition;
    }

    /**
     * Some drawables should be updated on every trial/calibration point.
     * This method is responsible for updating the drawable.
     */
    protected abstract void nextDrawable();

    public abstract void setSpec (String spec);

    public abstract void scaleSize(double scale);

    public abstract SizeType getSize();
    public abstract String getSpec();
}