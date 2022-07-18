package org.xper.allen.nafc.blockgen;

import org.xper.allen.nafc.blockgen.psychometric.PsychometricTrial;

import java.util.LinkedList;
import java.util.List;

public class PsychometricTrialListFactory implements TrialListFactory {

    int numTrialsPerImage;
    BlockParam<Lims> noiseChanceBlockParam;

    public PsychometricTrialListFactory(int numTrialsPerImage, BlockParam<Lims> noiseChanceBlockParam) {
        this.numTrialsPerImage = numTrialsPerImage;
        this.noiseChanceBlockParam = noiseChanceBlockParam;
    }

    @Override
    public List<Trial> createTrials() {
        List<Lims> noiseChances = noiseChanceBlockParam.getTrialList(numTrialsPerImage);


        List<Trial> trials = new LinkedList<>();

        trials.add(new PsychometricTrial(
                generator,
                nuDistractors,
                psychometricIds,
                trialParameters
        ));
    }
}
