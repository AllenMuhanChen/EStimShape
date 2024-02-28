package org.xper.allen.monitorlinearization;

import org.xper.allen.nafc.blockgen.AbstractTrialGenerator;
import org.xper.drawing.RGBColor;

import java.util.Collections;

public class MonLinTrialGenerator extends AbstractTrialGenerator<MonLinStim> {

    public int numStepsPerColor = 100;

    private final RGBColor[] colors = new RGBColor[]{
        new RGBColor(1,0,0),
        new RGBColor(0,1,0),
        new RGBColor(0,0,1)
    };

    @Override
    protected void addTrials() {
        for (RGBColor color : colors) {
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


}