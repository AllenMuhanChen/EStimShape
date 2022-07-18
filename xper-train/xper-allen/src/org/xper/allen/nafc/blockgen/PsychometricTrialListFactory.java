package org.xper.allen.nafc.blockgen;

import org.xper.allen.nafc.blockgen.psychometric.PsychometricTrial;

import java.util.LinkedList;
import java.util.List;

public class PsychometricTrialListFactory implements TrialListFactory {

    int numTrialsPerImage;
    TypeFrequency<Lims> noiseChanceTypeFrequency;
    
    public PsychometricTrialListFactory(int numTrialsPerImage, TypeFrequency<Lims> noiseChanceTypeFrequency) {
        this.numTrialsPerImage = numTrialsPerImage;
        this.noiseChanceTypeFrequency = noiseChanceTypeFrequency;
    }

    @Override
    public List<Trial> createTrials() {
        List<Lims> noiseChances = noiseChanceTypeFrequency.getTrialList(numTrialsPerImage);


        List<Trial> trials = new LinkedList<>();

        trials.add(new PsychometricTrial(
                generator,
                numDistractors,
                psychometricIds,
                trialParameters
        ));
    }
}
