package org.xper.allen.rfplot;

import org.xper.allen.monitorlinearization.LookUpTableCorrector;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.gabor.Gabor;
import org.xper.rfplot.drawing.gabor.IsoGaborSpec;

public class IsochromaticGabor extends Gabor {

    IsoGaborSpec gaborSpec;
    double luminanceCandela;
    private LookUpTableCorrector lutCorrector;

    public IsochromaticGabor(IsoGaborSpec gaborSpec, double luminanceCandela, LookUpTableCorrector lutCorrector) {
        super();
        this.gaborSpec = gaborSpec;
        this.luminanceCandela = luminanceCandela;
        this.lutCorrector = lutCorrector;

        stepsPerHalfCycle = 256;
//        stepsPerHalfCycle = 25;
    }

    //    ColourConverter.WhitePoint whitePoint = ColourConverter.WhitePoint.D65;


    @Override
    protected float[] modulateColor(float modFactor) {
        double min = 10;
        double max = 290;
        double targetCandela = modFactor * luminanceCandela;
        targetCandela = Math.max(min, Math.min(max, targetCandela));

//        double range = 280;
//        double targetCandela = luminanceCandela - range/2 + modFactor * range/2;

        // Convert RGB to Lab
        RGBColor corrected;
        if (gaborSpec.type.equals("Red")) {
            corrected = lutCorrector.correctSingleColor(targetCandela, "red");
        } else if (gaborSpec.type.equals("Green")) {
            corrected = lutCorrector.correctSingleColor(targetCandela, "green");
        } else if (gaborSpec.type.equals("Yellow")) {
            corrected = lutCorrector.correctSingleColor(targetCandela, "yellow");
        } else if (gaborSpec.type.equals("Cyan")) {
            corrected = lutCorrector.correctSingleColor(targetCandela, "cyan");
        } else if (gaborSpec.type.equals("Gray")){
            corrected = lutCorrector.correctSingleColor(targetCandela, "gray");
        }else {
            throw new RuntimeException("Unknown color space: " + gaborSpec.type);
        }





//        double [] lab = ColourConverter.getLab(new Color(color.getRed(), color.getGreen(), color.getBlue()), whitePoint);
//
//        // Modulate the L component for brightness
//        lab[0] = lab[0] * modFactor; // Ensure L stays within bounds
//
//        // Convert back to RGB
//        double[] modulatedRGB = ColourConverter.labToRGB(lab[0], lab[1], lab[2], whitePoint);
//
//        // Return as an array for OpenGL
//        float[] rgb = new float[3];
//        //convert back to 0-1 scale
//        rgb[0] = (float) (modulatedRGB[0]);
//        rgb[1] = (float) (modulatedRGB[1]);
//        rgb[2] = (float) (modulatedRGB[2]);

        return new float[]{corrected.getRed(), corrected.getGreen(), corrected.getBlue()};
    }

    @Override
    public IsoGaborSpec getGaborSpec() {
        return gaborSpec;
    }

    public void setGaborSpec(IsoGaborSpec gaborSpec) {
        this.gaborSpec = gaborSpec;
    }

    @Override
    public void setDefaultSpec() {
        setGaborSpec(new IsoGaborSpec());
        getGaborSpec().setPhase(0);
        getGaborSpec().setFrequency(1);
        getGaborSpec().setOrientation(0);
        getGaborSpec().setAnimation(true);
        getGaborSpec().setSize(5);
        getGaborSpec().setXCenter(0);
        getGaborSpec().setYCenter(0);
    }

    public String getSpec() {
        return getGaborSpec().toXml();
    }

    public void setSpec(String spec) {
        recalculateTextureIfChangeSigma(spec);
        this.setGaborSpec(IsoGaborSpec.fromXml(spec));

    }

    private void recalculateTextureIfChangeSigma(String spec) {
        String oldSpec = getSpec();
        IsoGaborSpec oldGabor = IsoGaborSpec.fromXml(oldSpec);
        double oldSigma = oldGabor.getDiameter();
        double newSigma = IsoGaborSpec.fromXml(spec).getDiameter();
        if (oldSigma != newSigma) {
            recalculateTexture();
        }
    }
}