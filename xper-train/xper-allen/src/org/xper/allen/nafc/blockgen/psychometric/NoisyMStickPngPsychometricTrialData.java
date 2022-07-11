package org.xper.allen.nafc.blockgen.psychometric;

import org.xper.allen.nafc.blockgen.psychometric.NoisyTrialParameters;
import org.xper.allen.nafc.vo.NoiseParameters;

import com.thoughtworks.xstream.XStream;

public class NoisyMStickPngPsychometricTrialData {
	
	NoiseParameters noiseParameters;
	NoisyTrialParameters trialGenData;
	static XStream s = new XStream();
	
	static {
		s.alias("NoisyMStickPngPsychometricTrialData", NoisyMStickPngPsychometricTrialData.class);
	}
	
	public NoisyMStickPngPsychometricTrialData(NoiseParameters noiseParameters,
			NoisyTrialParameters trialGenData) {
		super();
		this.noiseParameters = noiseParameters;
		this.trialGenData = trialGenData;
	}

	public String toXml(NoisyMStickPngPsychometricTrialData data) {
		return s.toXML(data);
	}

	public String toXml() {
		return toXml(this);
	}

	
	public NoiseParameters getNoiseData() {
		return noiseParameters;
	}

	public void setNoiseData(NoiseParameters noiseParameters) {
		this.noiseParameters = noiseParameters;
	}

	public NoisyTrialParameters getTrialGenData() {
		return trialGenData;
	}

	public void setTrialGenData(NoisyTrialParameters trialGenData) {
		this.trialGenData = trialGenData;
	}
	
	

}