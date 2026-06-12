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
 * when it sees a "LIGHTING_LEFT" / "LIGHTING_RIGHT" stim_type written by the Python
 * LightingSideTest.
 */
public class LightingGAStim extends GAStim<GAMatchStick, AllenMStickData> {

    // Front light is {0, 0, 500, 1}; rotate it 45 degrees about the vertical (Y) axis.
    // +x is screen-right, so RIGHT has +x and LEFT has -x; z stays positive (in front).
    private static final float FORWARD = 500.0f;
    private static final float OFFSET_45 = (float) (FORWARD * Math.sin(Math.toRadians(45.0)));
    public static final float[] LEFT_LIGHT = {-OFFSET_45, 0.0f, OFFSET_45, 1.0f};
    public static final float[] RIGHT_LIGHT = {OFFSET_45, 0.0f, OFFSET_45, 1.0f};

    private final float[] lightPosition;

    public LightingGAStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, float[] lightPosition) {
        // "PARENT" texture + no average-RGB swap: keep the parent's texture and color as-is.
        super(stimId, generator, parentId, "PARENT", false);
        this.lightPosition = lightPosition;
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
