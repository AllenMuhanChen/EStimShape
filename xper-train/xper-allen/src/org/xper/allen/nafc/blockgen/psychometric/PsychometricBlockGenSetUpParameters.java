package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;

public class PsychometricBlockGenSetUpParameters {
    private final PsychometricFactoryParameters psychometricFactoryParameters;
    private final RandFactoryParameters randFactoryParameters;

    public PsychometricBlockGenSetUpParameters(PsychometricFactoryParameters psychometricFactoryParameters, RandFactoryParameters randFactoryParameters) {
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
