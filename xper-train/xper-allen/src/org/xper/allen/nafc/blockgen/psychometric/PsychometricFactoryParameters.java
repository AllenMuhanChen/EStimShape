package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.*;

import java.util.List;

public class PsychometricFactoryParameters {
   int numTrialsPerImage;
   List<NoisyTrialParameters> trialParameters;
   List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors;

   private PsychometricFactoryParameters(int numTrialsPerImage, List<NoisyTrialParameters> trialParameters, List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors) {
      this.numTrialsPerImage = numTrialsPerImage;
      this.trialParameters = trialParameters;
      this.numPsychometricDistractors = numPsychometricDistractors;
   }

   public static PsychometricFactoryParameters create(int numTrialsPerImage, List<NoisyTrialParameters> trialParameters, List<NumberOfDistractorsForPsychometricTrial> numPsychometricDistractors) {
      return new PsychometricFactoryParameters(numTrialsPerImage, trialParameters, numPsychometricDistractors);
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
}
