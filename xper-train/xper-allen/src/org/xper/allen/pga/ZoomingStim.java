package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.composition.morph.MorphedMatchStick;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.Coordinates2D;
import org.xper.drawing.RGBColor;

public class ZoomingStim extends GAStim<GAMatchStick, AllenMStickData> {

    private final Integer compIdInRF;
    private double scaleFactor = 1;

    public ZoomingStim(Long stimId, FromDbGABlockGenerator generator, Long parentId, Integer compIdInRF, Coordinates2D coords, double magnitude, String textureType, RGBColor color) {
        super(stimId, generator, parentId, coords, textureType, color,
                RFStrategy.PARTIALLY_INSIDE);
        this.compIdInRF = compIdInRF;
    }

    @Override
    protected GAMatchStick createMStick() {

        GAMatchStick mStick = new GAMatchStick(
                generator.getReceptiveField(),
                RFStrategy.PARTIALLY_INSIDE
        );
        System.out.println("Scale Factor: " + scaleFactor);
        sizeDiameterDegrees = scaleFactor * RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees());
        mStick.setProperties(sizeDiameterDegrees, textureType);
        mStick.setStimColor(color);
        mStick.genPartialFromFile(
                generator.getGeneratorSpecPath() + "/" + parentId + "_spec.xml",
                compIdInRF);


        return mStick;
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
                System.out.println(me.getMessage());
                System.out.println("FAILED TO CREATE PARTIAL MATCHSTICK OF TYPE: " + this.getClass().getSimpleName() + " SCALING SIZE DOWN AND TRYING AGAIN...");
                scaleFactor = scaleFactor * 0.9;

            }
        }

        if (nTries == maxTries && mStick == null) {
            throw new RuntimeException("CRITICAL ERROR: COULD NOT GENERATE MORPHED MATCHSTICK  OF TYPE" + this.getClass().getSimpleName()+"AFTER " + maxTries + " TRIES");
        }


        saveMStickSpec(mStick);

        AllenMStickData mStickData = (AllenMStickData) mStick.getMStickData();
        drawCompMaps(mStick);
        String pngPath = drawPngs(mStick);
        writeStimSpec(pngPath, mStickData);

        //write additional data here?
        writeStimData();
    }
}