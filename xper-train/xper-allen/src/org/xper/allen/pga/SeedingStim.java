package org.xper.allen.pga;

import org.xper.allen.drawing.composition.AllenMStickData;
import org.xper.allen.drawing.ga.GAMatchStick;
import org.xper.drawing.RGBColor;
import java.util.Random;

public class SeedingStim extends GAStim<GAMatchStick, AllenMStickData> {
    private static final Random random = new Random();

    public SeedingStim(Long stimId, FromDbGABlockGenerator generator, String textureType, RGBColor color) {
        super(stimId, generator, 0L, textureType);
        this.color = color;
        this.textureType = textureType;
    }

    @Override
    protected void chooseRFStrategy() {
        rfStrategy = RFStrategy.COMPLETELY_INSIDE;
    }

    @Override
    protected void chooseSize() {
        double maxSizeDiameterDegrees = RFUtils.calculateMStickMaxSizeDiameterDegrees(rfStrategy, generator.rfSource.getRFRadiusDegrees());
        double minSizeDiameterDegrees = maxSizeDiameterDegrees / 2;

        sizeDiameterDegrees = minSizeDiameterDegrees + random.nextDouble() * (maxSizeDiameterDegrees - minSizeDiameterDegrees);
    }

    @Override
    protected void chooseColor() {
        // Color set in constructor. This should be the max bright we want in shade

        // See if texture is Shade or Specular

    }

    @Override
    protected void chooseUnderlyingTexture() {
        if (is2d){
            this.underlyingTexture = Math.random() < 0.5 ? "SHADE" : "SPECULAR";
        } else{
            this.underlyingTexture = this.textureType;
        }
    }


    @Override
    protected GAMatchStick createMStick() {
        GAMatchStick mStick = new GAMatchStick(
                generator.getReceptiveField(),
                rfStrategy);


        mStick.setProperties(sizeDiameterDegrees, textureType, contrast);
        mStick.setContrast(contrast);
        mStick.setStimColor(color);

        mStick.genMatchStickRand();

        return mStick;
    }
}