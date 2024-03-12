package org.xper.allen.monitorlinearization;

import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.drawing.RGBColor;
import org.xper.rfplot.drawing.gabor.Gamma;
import org.xper.rfplot.drawing.gabor.GammaCorrection;

public class MonLinTrialGenerator extends AbstractTrialGenerator<MonLinStim> {
    public String mode;
    public int numStepsPerColor = 100;

    private final RGBColor[] linearColors = new RGBColor[]{
        new RGBColor(1,0,0),
        new RGBColor(0,1,0),
        new RGBColor(0,0,1)
    };

    GammaCorrection correction = new GammaCorrection(
            new Gamma(650.1819996419763, 2.373251366723648),
            new Gamma(1082.122693368536, 2.440940615232001),
            new Gamma(248.05343859631856, 2.173167747138167)
    );

    @Override
    protected void addTrials() {
        if (mode.equals("Isoluminant")){
            addIsoluminantTrials();
        } else {
            addLinearTrials();
        }
    }

    private void addIsoluminantTrials() {
        int steps = 100;
        double r;
        double g;
        double b;
        for (int i = 0; i < steps; i++) {
            float modFactor = (float) i / (steps-1);
            r = interpolate(1.0, 0, modFactor);
            g = 1 - r;
            b = 0;
            RGBColor corrected = correction.correct(new RGBColor((float) r, (float) g, (float) b), 200);
            stims.add(new MonLinStim(this, corrected));
        }
    }

    private void addLinearTrials() {
        for (RGBColor color : linearColors) {
            for (int i = 0; i < numStepsPerColor; i++) {
                RGBColor newColor = new RGBColor(
                    color.getRed() * i / (numStepsPerColor-1),
                    color.getGreen() * i / (numStepsPerColor-1),
                    color.getBlue() * i / (numStepsPerColor-1)
                );

                stims.add(new MonLinStim(this, newColor));
            }
        }
    }

    protected void shuffleTrials() {
    }

    private double interpolate(double value1, double value2, float factor) {
        return value1 + (value2 - value1) * factor;
    }


}