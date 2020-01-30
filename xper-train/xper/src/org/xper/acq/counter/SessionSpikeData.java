package org.xper.acq.counter;

import java.util.ArrayList;
import java.util.List;

public class SessionSpikeData {
	List<TrialStageData> trialStageData = new ArrayList<TrialStageData>();
	List<Double> spikePerSec = new ArrayList<Double>();
	double sampleFrequency;
	
	public List<TrialStageData> getTrialStageData() {
		return trialStageData;
	}
	public void setTrialStageData(List<TrialStageData> trialStageData) {
		this.trialStageData = trialStageData;
	}
	public List<Double> getSpikePerSec() {
		return spikePerSec;
	}
	public void setSpikePerSec(List<Double> spikePerSec) {
		this.spikePerSec = spikePerSec;
	}
	public double getSampleFrequency() {
		return sampleFrequency;
	}
	public void setSampleFrequency(double sampleFrequency) {
		this.sampleFrequency = sampleFrequency;
	}
	public void addTrialStageData (TrialStageData d) {
		trialStageData.add(d);
	}
	
	public void addSpikePerSec (Double d) {
		spikePerSec.add(d);
	}
}
