package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.PsychometricTrialListFactory;
import org.xper.allen.nafc.blockgen.rand.RandFactoryParameters;
import org.xper.allen.nafc.blockgen.rand.RandTrialListFactory;

public class PsychometricBlockGen extends AbstractPsychometricTrialGenerator {

    private PsychometricFactoryParameters psychometricFactoryParameters;
    private RandFactoryParameters randFactoryParameters;


    public void setUp(PsychometricBlockParameters psychometricBlockParameters){
        this.psychometricFactoryParameters = psychometricBlockParameters.getPsychometricFactoryParameters();
        this.randFactoryParameters = psychometricBlockParameters.getRandFactoryParameters();
    }

    @Override
    protected void addTrials() {
        addPsychometricTrials(psychometricFactoryParameters);
        addRandTrials(randFactoryParameters);
    }

    private void addPsychometricTrials(PsychometricFactoryParameters psychometricFactoryParameters) {
        PsychometricTrialListFactory psychometricFactory = new PsychometricTrialListFactory(
                this, psychometricFactoryParameters
        );
        trials.addAll(psychometricFactory.createTrials());
    }

    protected void addRandTrials(RandFactoryParameters randFactoryParameters) {
        RandTrialListFactory randFactory = new RandTrialListFactory(
                this, randFactoryParameters);
        trials.addAll(randFactory.createTrials());
    }

    public String getGeneratorPngPath() {
        return generatorPngPath;
    }

    public void setGeneratorPngPath(String generatorPngPath) {
        this.generatorPngPath = generatorPngPath;
    }

    public String getExperimentPngPath() {
        return experimentPngPath;
    }

    public void setExperimentPngPath(String experimentPngPath) {
        this.experimentPngPath = experimentPngPath;
    }

    public String getGeneratorSpecPath() {
        return generatorSpecPath;
    }

    public void setGeneratorSpecPath(String generatorSpecPath) {
        this.generatorSpecPath = generatorSpecPath;
    }


}
