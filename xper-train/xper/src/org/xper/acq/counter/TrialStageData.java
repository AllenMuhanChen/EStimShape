package org.xper.acq.counter;

public class TrialStageData {
	int startSampleIndex;
	int stopSampleIndex;
	int [] spikeData;
	public int getStartSampleIndex() {
		return startSampleIndex;
	}
	public void setStartSampleIndex(int startSampleIndex) {
		this.startSampleIndex = startSampleIndex;
	}
	public int getStopSampleIndex() {
		return stopSampleIndex;
	}
	public void setStopSampleIndex(int stopSampleIndex) {
		this.stopSampleIndex = stopSampleIndex;
	}
	public int[] getSpikeData() {
		return spikeData;
	}
	public void setSpikeData(int[] spikeData) {
		this.spikeData = spikeData;
	}
}
