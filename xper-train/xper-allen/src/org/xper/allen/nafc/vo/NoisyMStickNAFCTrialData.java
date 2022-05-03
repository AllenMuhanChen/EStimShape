package org.xper.allen.nafc.vo;

import java.util.List;

import org.xper.allen.drawing.composition.metricmorphs.MetricMorphParams;
import org.xper.allen.drawing.composition.qualitativemorphs.QualitativeMorphParams;

import com.thoughtworks.xstream.XStream;

public class NoisyMStickNAFCTrialData {
	
	NoisyMStickNAFCTrialGenData trialGenData;
	NoiseData noiseData;
	List<QualitativeMorphParams> qualitativeMorphParameters;
	MetricMorphParams metricMorphParameters;

	
	public NoisyMStickNAFCTrialData(NoisyMStickNAFCTrialGenData trialGenData, NoiseData noiseData,
			List<QualitativeMorphParams> qualitativeMorphParameters, MetricMorphParams metricMorphParameters) {
		super();
		this.trialGenData = trialGenData;
		this.noiseData = noiseData;
		this.qualitativeMorphParameters = qualitativeMorphParameters;
		this.metricMorphParameters = metricMorphParameters;
	}

	public NoisyMStickNAFCTrialData() {
	}
	
	static XStream s = new XStream();
	
	static {
		s.alias("NoisyMStickNAFCTrialData", NoisyMStickNAFCTrialData.class);
	}
	
	public static String toXml(NoisyMStickNAFCTrialData data) {
		return s.toXML(data);
	}
	
	public String toXml() {
		return toXml(this);
	}
	
	public NoisyMStickNAFCTrialGenData getTrialGenData() {
		return trialGenData;
	}
	public void setTrialGenData(NoisyMStickNAFCTrialGenData trialGenData) {
		this.trialGenData = trialGenData;
	}
	public NoiseData getNoiseData() {
		return noiseData;
	}
	public void setNoiseData(NoiseData noiseData) {
		this.noiseData = noiseData;
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
