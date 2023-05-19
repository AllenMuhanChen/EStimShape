package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.*;
import org.xper.intan.stimulation.EStimParameters;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class PsychometricFactoryParameters {
   int numTrialsPerImage;
   List<NoisyTrialParameters> trialParameters;
   List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors;
   Map<Long, EStimParameters> eStimParametersForSetIds;

   private PsychometricFactoryParameters(int numTrialsPerImage, List<NoisyTrialParameters> trialParameters, List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors) {
      this.numTrialsPerImage = numTrialsPerImage;
      this.trialParameters = trialParameters;
      this.numPsychometricDistractors = numPsychometricDistractors;
      this.eStimParametersForSetIds = new HashMap<>();
   }

   private PsychometricFactoryParameters(int numTrialsPerImage, List<NoisyTrialParameters> trialParameters, List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors, Map<Long, EStimParameters> eStimParametersForSetIds) {
      this.numTrialsPerImage = numTrialsPerImage;
      this.trialParameters = trialParameters;
      this.numPsychometricDistractors = numPsychometricDistractors;
      this.eStimParametersForSetIds = eStimParametersForSetIds;
   }

   public static PsychometricFactoryParameters createWithNoEStim(int numTrialsPerImage, List<NoisyTrialParameters> trialParameters, List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors) {
      return new PsychometricFactoryParameters(numTrialsPerImage, trialParameters, numPsychometricDistractors);
   }

   public static PsychometricFactoryParameters create(int numTrialsPerImage, List<NoisyTrialParameters> trialParameters, List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors, Map<Long, EStimParameters> eStimParametersForSetIds) {
      return new PsychometricFactoryParameters(numTrialsPerImage, trialParameters, numPsychometricDistractors, eStimParametersForSetIds);
   }

   public int getNumTrialsPerImage() {
      return numTrialsPerImage;
   }

   public List<NoisyTrialParameters> getTrialParameters() {
      return trialParameters;
   }

   public List<NumberOfDistractorsForPsychometricTrial> getNumDistractors() {
      return numPsychometricDistractors;
   }

   public Map<Long, EStimParameters> geteStimParametersForSetIds() {
      return eStimParametersForSetIds;
   }

   public void seteStimParametersForSetIds(Map<Long, EStimParameters> eStimParametersForSetIds) {
      this.eStimParametersForSetIds = eStimParametersForSetIds;
   }
}