package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;

import java.awt.*;

public class NoisyPngFixationTrialParameters {
    double noiseChance;
    Lims distanceLims;
    double size;
    Color color;

    public NoisyPngFixationTrialParameters(double noiseChance, Lims distanceLims, double size, Color color) {
        this.noiseChance = noiseChance;
        this.distanceLims = distanceLims;
        this.size = size;
        this.color = color;
    }

    public double getNoiseChance() {
        return noiseChance;
    }

    public void setNoiseChance(double noiseChance) {
        this.noiseChance = noiseChance;
    }

    public Color getColor() {
        return color;
    }

    public void setColor(Color color) {
        this.color = color;
    }

    public Lims getDistanceLims() {
        return distanceLims;
    }

    public void setDistanceLims(Lims distanceLims) {
        this.distanceLims = distanceLims;
    }

    public double getSize() {
        return size;
    }

    public void setSize(double size) {
        this.size = size;
    }


}