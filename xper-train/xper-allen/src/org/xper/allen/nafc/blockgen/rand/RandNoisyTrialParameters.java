package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.vo.NoiseParameters;

import com.thoughtworks.xstream.XStream;

public class RandNoisyTrialParameters extends NoisyTrialParameters {

	NumberOfDistractorsForRandTrial numDistractors;
	NumberOfMorphCategories numMorphCategories;

	public RandNoisyTrialParameters(NumberOfDistractorsForRandTrial numDistractors, NumberOfMorphCategories numMorphCategories, NoisyTrialParameters noisyTrialParameters) {
		super(noisyTrialParameters.getSampleDistanceLims(), noisyTrialParameters.getChoiceDistanceLims(), noisyTrialParameters.getSize(), noisyTrialParameters.getEyeWinSize(), noisyTrialParameters.getNoiseParameters());
		this.numDistractors = numDistractors;
		this.numMorphCategories = numMorphCategories;
		this.numChoices = numDistractors.getTotalNumDistractors()+1;
	}

	public RandNoisyTrialParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinSize,
									NoiseParameters noiseParameters, NumberOfDistractorsForRandTrial numDistractors,
									NumberOfMorphCategories numMorphCategories) {
		super(sampleDistanceLims, choiceDistanceLims, size, eyeWinSize, noiseParameters);
		this.numDistractors = numDistractors;
		this.numMorphCategories = numMorphCategories;
		this.numChoices = numDistractors.getTotalNumDistractors()+1;
	}

	private int numChoices;
	
	static XStream s = new XStream();

	static {
		s.alias("RandNoisyTrialParameters", RandNoisyTrialParameters.class);
	}

	public String toXml(RandNoisyTrialParameters data) {
		return s.toXML(data);
	}

	public String toXml() {
		return toXml(this);
	}

	
	public NumberOfDistractorsForRandTrial getNumDistractors() {
		return numDistractors;
	}

	public void setNumDistractors(NumberOfDistractorsForRandTrial numDistractors) {
		this.numDistractors = numDistractors;
	}

	public NumberOfMorphCategories getNumMorphCategories() {
		return numMorphCategories;
	}

	public void setNumMorphCategories(NumberOfMorphCategories numMorphCategories) {
		this.numMorphCategories = numMorphCategories;
	}

	public int getNumChoices() {
		return numChoices;
	}


	
	
}