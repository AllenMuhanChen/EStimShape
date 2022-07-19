package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.Lims;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;
import org.xper.allen.nafc.blockgen.HandicappedNAFCTrialParameters;
import org.xper.allen.nafc.vo.NoiseParameters;

import com.thoughtworks.xstream.XStream;

public class NoisyTrialParameters extends NAFCTrialParameters{

	NoiseParameters noiseParameters;

	public NoisyTrialParameters(NoiseParameters noiseParameters, NAFCTrialParameters nafcTrialParameters){
		super(nafcTrialParameters);
		this.noiseParameters = noiseParameters;
	}

	public NoisyTrialParameters(NoisyTrialParameters other) {
		this.noiseParameters = other.noiseParameters;
	}

	public NoisyTrialParameters(Lims sampleDistanceLims, Lims choiceDistanceLims, double size, double eyeWinSize,
								NoiseParameters noiseParameters) {
		super(sampleDistanceLims, choiceDistanceLims, size, eyeWinSize);
		this.noiseParameters = noiseParameters;
	}

	static XStream s = new XStream();

	static {
		s.alias("NoisyTrialParameters", NoisyTrialParameters.class);
	}


	public String toXml(NoisyTrialParameters data) {
		return s.toXML(data);
	}

	public String toXml() {
		return toXml(this);
	}

	public NoiseParameters getNoiseParameters() {
		return noiseParameters;
	}

	public void setNoiseData(NoiseParameters noiseParameters) {
		this.noiseParameters = noiseParameters;
	}
}