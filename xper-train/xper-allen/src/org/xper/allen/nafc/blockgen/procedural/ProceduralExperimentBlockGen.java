package org.xper.allen.nafc.blockgen.procedural;

import org.xper.Dependency;
import org.xper.allen.Stim;
import org.xper.allen.nafc.blockgen.AbstractMStickPngTrialGenerator;
import org.xper.allen.nafc.blockgen.psychometric.AbstractPsychometricTrialGenerator;

public class ProceduralExperimentBlockGen extends AbstractMStickPngTrialGenerator<ProceduralStim> {

    @Dependency
    String generatorNoiseMapPath;

    @Dependency
    String experimentNoiseMapPath;

    @Override
    protected void addTrials() {

    }

    public String getGeneratorNoiseMapPath() {
        return generatorNoiseMapPath;
    }

    public void setGeneratorNoiseMapPath(String generatorNoiseMapPath) {
        this.generatorNoiseMapPath = generatorNoiseMapPath;
    }

    public String getExperimentNoiseMapPath() {
        return experimentNoiseMapPath;
    }

    public void setExperimentNoiseMapPath(String experimentNoiseMapPath) {
        this.experimentNoiseMapPath = experimentNoiseMapPath;
    }
}