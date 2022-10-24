package org.xper.allen.nafc.blockgen.rand;

import java.util.List;

import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;
import org.xper.allen.nafc.vo.NoiseParameters;

import com.thoughtworks.xstream.XStream;

public class RandNoisyMStickTrialMessage {

	RandNoisyTrialParameters trialGenData;
	NoiseParameters noiseParameters;
	List<QualitativeMorphParams> qualitativeMorphParameters;
	MetricMorphParams metricMorphParameters;
	static XStream s = new XStream();
	static {
		s.alias("NoisyMStickNAFCTrialData", RandNoisyMStickTrialMessage.class);
	}
	public RandNoisyMStickTrialMessage(RandNoisyTrialParameters trialGenData, NoiseParameters noiseParameters,
			List<QualitativeMorphParams> qualitativeMorphParameters, MetricMorphParams metricMorphParameters) {
		super();
		this.trialGenData = trialGenData;
		this.noiseParameters = noiseParameters;
		this.qualitativeMorphParameters = qualitativeMorphParameters;
		this.metricMorphParameters = metricMorphParameters;
	}

	public RandNoisyMStickTrialMessage() {
	}

	public String toXml(RandNoisyMStickTrialMessage data) {
		return s.toXML(data);
	}

	public String toXml() {
		return toXml(this);
	}

	public RandNoisyTrialParameters getTrialGenData() {
		return trialGenData;
	}
	public void setTrialGenData(RandNoisyTrialParameters trialGenData) {
		this.trialGenData = trialGenData;
	}
	public NoiseParameters getNoiseData() {
		return noiseParameters;
	}
	public void setNoiseData(NoiseParameters noiseParameters) {
		this.noiseParameters = noiseParameters;
	}

	public List<QualitativeMorphParams> getQualitativeMorphParameters() {
		return qualitativeMorphParameters;
	}

	public void setQualitativeMorphParameters(List<QualitativeMorphParams> qualitativeMorphParameters) {
		this.qualitativeMorphParameters = qualitativeMorphParameters;
	}

	public MetricMorphParams getMetricMorphParameters() {
		return metricMorphParameters;
	}

	public void setMetricMorphParameters(MetricMorphParams metricMorphParameters) {
		this.metricMorphParameters = metricMorphParameters;
	}
	

}