package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.allen.drawing.ga.LightingGAMatchStick;

import javax.vecmath.Point3d;

/**
 * GA side-test stim that re-renders the parent stimulus under a different lighting direction.
 *
 * Carries the old AlexNet LightingPostHocGenerator idea into the neural GA. Reproduces the
 * parent faithfully (same shape, texture, color, size, position) - only the OpenGL light
 * position changes (see {@link LightingGAMatchStick}). Created by {@link FromDbGABlockGenerator}
 * when it sees a "LIGHTING" stim_type written by the Python LightingSideTest; the lighting
 * direction is carried in the stimulus's mutation_magnitude (rotation angle in degrees).
 */
public class LightingGAStim extends GAStim<GAMatchStick, AllenMStickData> {

    // Front light is {0, 0, 500, 1}; rotating it about the vertical (Y) axis keeps z forward and
    // sweeps x left/right.
    private static final float FORWARD = 500.0f;

    private final float[] lightPosition;

    public LightingGAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, double lightAngleDegrees) {
        // "PARENT" texture + no average-RGB swap: keep the parent's texture and color as-is.
        super(stimId, generator, parentId, "PARENT", false);
        this.lightPosition = lightPositionForAngle(lightAngleDegrees);
    }

    /**
     * The OpenGL light position for the front light {0, 0, 500, 1} rotated by {@code angleDegrees}
     * about the vertical (Y) axis. 0 degrees is the front light; positive sweeps toward +x.
     */
    public static float[] lightPositionForAngle(double angleDegrees) {
        double radians = Math.toRadians(angleDegrees);
        float x = (float) (FORWARD * Math.sin(radians));
        float z = (float) (FORWARD * Math.cos(radians));
        return new float[]{x, 0.0f, z, 1.0f};
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = rfStrategyManager.readProperty(parentId);
    }

    @Override
    protected void chooseSize() {
        sizeDiameterDegrees = sizeManager.readProperty(parentId);
    }

    @Override
    protected void choosePosition() {
        position = positionManager.readProperty(parentId);
    }

    @Override
    protected GAMatchStick createMStick() {
        // Faithfully redraw the parent at its own center of mass (mirrors ShuffleGAStim), but
        // under the side test's light position.
        Point3d centerOfMass = getTargetsCenterOfMass(parentId);
        LightingGAMatchStick mStick = new LightingGAMatchStick(centerOfMass, lightPosition);
        mStick.setRf(generator.getReceptiveField());
        mStick.setProperties(sizeDiameterDegrees, textureType, is2d, contrast);
        mStick.setStimColor(color);
        mStick.genMatchStickFromFile(generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml");
        return mStick;
    }

    @Override
    public void writeStim() {
        setProperties();
        GAMatchStick mStick = createMStick();

        // GAStim.writeStimProperties() persists averageRGB and NPEs on null, so populate it.
        averageRGB = generator.getPngMaker().getWindow().calculateAverageRGB(mStick);

        saveMStickSpec(mStick);
        String pngPath = drawPngs(mStick);
        drawThumbnails(mStick);

        AllenMStickData mStickData = (AllenMStickData) mStick.getMStickData();
        writeStimSpec(pngPath, mStickData);

        writeStimProperties();
    }
}
