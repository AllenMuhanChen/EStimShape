package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;

public class NoisyPngFixationParameters {
    NoiseParameters noiseParameters;
    Lims distanceLims;
    double size;

    public NoisyPngFixationParameters(NoiseParameters noiseParameters, Lims distanceLims, double size) {
        this.noiseParameters = noiseParameters;
        this.distanceLims = distanceLims;
        this.size = size;


    }

    public NoiseParameters getNoiseParameters() {
        return noiseParameters;
    }

    public void setNoiseParameters(NoiseParameters noiseParameters) {
        this.noiseParameters = noiseParameters;
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
