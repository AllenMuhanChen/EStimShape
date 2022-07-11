package org.xper.allen.nafc.blockgen.rand;

import org.xper.allen.nafc.blockgen.HandicappedNAFCTrialParameters;
import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.vo.NoiseParameters;

import com.thoughtworks.xstream.XStream;

public class RandNoisyTrialParameters extends NoisyTrialParameters {

	NumberOfDistractorsByMorphType numDistractors;
	NumberOfMorphCategories numMorphCategories;

	
	public RandNoisyTrialParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinSize,
			NoiseParameters noiseParameters, NumberOfDistractorsByMorphType numDistractors,
			NumberOfMorphCategories numMorphCategories) {
		super(sampleDistanceLims, choiceDistanceLims, size, eyeWinSize, noiseParameters);
		this.numDistractors = numDistractors;
		this.numMorphCategories = numMorphCategories;
	}

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

	
	public NumberOfDistractorsByMorphType getNumDistractors() {
		return numDistractors;
	}

	public void setNumDistractors(NumberOfDistractorsByMorphType numDistractors) {
		this.numDistractors = numDistractors;
	}

	public NumberOfMorphCategories getNumMorphCategories() {
		return numMorphCategories;
	}

	public void setNumMorphCategories(NumberOfMorphCategories numMorphCategories) {
		this.numMorphCategories = numMorphCategories;
	}


	
	
}