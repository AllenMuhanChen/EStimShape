package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.intan.EStimParameter;
import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;
import org.xper.intan.stimulation.EStimParameters;

import java.util.Map;

public class PsychometricBlockParameters {
    private final PsychometricFactoryParameters psychometricFactoryParameters;
    private final RandFactoryParameters randFactoryParameters;


    public PsychometricBlockParameters(PsychometricFactoryParameters psychometricFactoryParameters, RandFactoryParameters randFactoryParameters) {
        this.psychometricFactoryParameters = psychometricFactoryParameters;
        this.randFactoryParameters = randFactoryParameters;
    }

    public PsychometricFactoryParameters getPsychometricFactoryParameters() {
        return psychometricFactoryParameters;
    }

    public RandFactoryParameters getRandFactoryParameters() {
        return randFactoryParameters;
    }
}