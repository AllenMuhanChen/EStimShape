package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class PartialStim extends GAStim<GAMatchStick, AllenMStickData> {

    private final double magnitude;

    public PartialStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Coordinates2D coords, double magnitude, String textureType, RGBColor color, RFStrategy rfStrategy) {
        super(stimId, generator, parentId, coords, textureType, color, rfStrategy);
        this.magnitude = magnitude;

    }

    @Override
    protected GAMatchStick createMStick() {
        return null;
    }

    @Override
    public void writeStim() {
        int nTries = 0;
        GAMatchStick mStick = null;
        int maxTries = 100;
        while(nTries < maxTries) {
            nTries++;
            try {
                mStick = createMStick();
                System.out.println("SUCCESSFUL CREATION OF MORPHED MATCHSTICK OF TYPE: " + this.getClass().getSimpleName());
                break;
            } catch (MorphedMatchStick.MorphException me) {
                mStick = null;
                System.out.println("Morphing failed, trying again with new parameters");
            }
        }

        if (nTries == maxTries && mStick == null) {
            System.err.println("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName()+"AFTER 10 TRIES. GENERATING RAND...");
            mStick = createRandMStick();
        }


        saveMStickSpec(mStick);

        AllenMStickData mStickData = mStick.getMStickData();
        drawCompMaps(mStick);
        String pngPath = drawPngs(mStick);
        writeStimSpec(pngPath, mStickData);
    }
}