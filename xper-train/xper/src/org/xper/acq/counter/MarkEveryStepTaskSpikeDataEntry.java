package org.xper.acq.counter;

import java.util.ArrayList;
import java.util.List;

public class MarkEveryStepTaskSpikeDataEntry {
	long taskId;
	/**
	 * Spike positions for each stage of the trial
	 */
	List<TrialStageData> trialStageData = new ArrayList<TrialStageData>();
	List<Double> spikePerSec = new ArrayList<Double>();
	double sampleFrequency;
	public long getTaskId() {
		return taskId;
	}
	public void setTaskId(long taskId) {
		this.taskId = taskId;
	}
	public List<TrialStageData> getTrialStageData() {
		return trialStageData;
	}
	public void setTrialStageData(List<TrialStageData> data) {
		this.trialStageData = data;
	}
	public void addTrialStageData (TrialStageData d) {
		trialStageData.add(d);
	}
	public void addSpikePerSec (double r) {
		spikePerSec.add(r);
	}
	public TrialStageData getTrialStageData (int i) {
		return trialStageData.get(i);
	}
	public double getSpikePerSec(int i) {
		return spikePerSec.get(i);
	}
	public double getSampleFrequency() {
		return sampleFrequency;
	}
	public void setSampleFrequency(double sampleFrequency) {
		this.sampleFrequency = sampleFrequency;
	}
	public List<Double> getSpikePerSec() {
		return spikePerSec;
	}
	public void setSpikePerSec(List<Double> spikePerSec) {
		this.spikePerSec = spikePerSec;
	}
}
