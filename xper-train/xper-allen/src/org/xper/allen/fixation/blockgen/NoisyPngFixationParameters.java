package org.xper.allen.fixation.blockgen;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.vo.NoiseParameters;
import java.util.List;

public class NoisyPngFixationParameters {
    List<NoiseParameters> noiseParameters;
    Lims distanceLims;
    double size;

    public NoisyPngFixationParameters(List<NoiseParameters> noiseParameters, Lims distanceLims, double size) {
        this.noiseParameters = noiseParameters;
        this.distanceLims = distanceLims;
        this.size = size;
    }

    public List<NoiseParameters> getNoiseParameters() {
        return noiseParameters;
    }

    public void setNoiseParameters(List<NoiseParameters> noiseParameters) {
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
