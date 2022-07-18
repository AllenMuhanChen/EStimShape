package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.*;

public class PsychometricFactoryParameters {
   int numTrialsPerImage;
   TypeFrequency<NumberOfDistractorsForPsychometricTrial> numDistractorsTypeFrequency;
   TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency;

   public PsychometricFactoryParameters(int numTrialsPerImage, TypeFrequency<NumberOfDistractorsForPsychometricTrial> numDistractorsTypeFrequency, TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency) {
      this.numTrialsPerImage = numTrialsPerImage;
      this.numDistractorsTypeFrequency = numDistractorsTypeFrequency;
      this.trialParametersTypeFrequency = trialParametersTypeFrequency;
   }

   public int getNumTrialsPerImage() {
      return numTrialsPerImage;
   }

   public void setNumTrialsPerImage(int numTrialsPerImage) {
      this.numTrialsPerImage = numTrialsPerImage;
   }

   public TypeFrequency<NumberOfDistractorsForPsychometricTrial> getNumDistractorsTypeFrequency() {
      return numDistractorsTypeFrequency;
   }

   public void setNumDistractorsTypeFrequency(TypeFrequency<NumberOfDistractorsForPsychometricTrial> numDistractorsTypeFrequency) {
      this.numDistractorsTypeFrequency = numDistractorsTypeFrequency;
   }

   public TypeFrequency<NoisyTrialParameters> getTrialParametersTypeFrequency() {
      return trialParametersTypeFrequency;
   }

   public void setTrialParametersTypeFrequency(TypeFrequency<NoisyTrialParameters> trialParametersTypeFrequency) {
      this.trialParametersTypeFrequency = trialParametersTypeFrequency;
   }
}
