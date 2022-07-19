package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.*;

public class PsychometricFactoryParameters {
   int numTrialsPerImage;
   TypeFrequency<NoisyTrialParameters> trialParameters;
   TypeFrequency<Integer> numPsychometricDistractors;
   TypeFrequency<Integer> numRandDistractors;

   public PsychometricFactoryParameters(int numTrialsPerImage, TypeFrequency<Integer> numPsychometricDistractors, TypeFrequency<Integer> numRandDistractors, TypeFrequency<NoisyTrialParameters> trialParameters) {
      this.numTrialsPerImage = numTrialsPerImage;
      this.trialParameters = trialParameters;
      this.numPsychometricDistractors = numPsychometricDistractors;
      this.numRandDistractors = numRandDistractors;
   }

   public int getNumTrialsPerImage() {
      return numTrialsPerImage;
   }

   public TypeFrequency<Integer> getNumPsychometricDistractors() {
      return numPsychometricDistractors;
   }

   public TypeFrequency<Integer> getNumRandDistractors() {
      return numRandDistractors;
   }

   public TypeFrequency<NoisyTrialParameters> getTrialParameters() {
      return trialParameters;
   }

   public void setTrialParameters(TypeFrequency<NoisyTrialParameters> trialParameters) {
      this.trialParameters = trialParameters;
   }
}
