package org.xper.acq.counter;

/**
 * This is the classical experiment setup.
 * Experiment setup: markers only show up during task stimulus presentation.
 * So Xper can find out the correspondence between marker switch and task id 
 * and therefore can decide from data in AcqData table the spike rate for each task.
 *  
 * @author g1uzaw
 *
 */
public class TaskSpikeDataEntry {
	long taskId;
	double spikePerSec;
	
	int startSampleIndex;
	int stopSampleIndex;
	double sampleFrequency;
	int [] spikeData;
	public double getSampleFrequency() {
		return sampleFrequency;
	}
	public void setSampleFrequency(double sampleFrequency) {
		this.sampleFrequency = sampleFrequency;
	}
	public int[] getSpikeData() {
		return spikeData;
	}
	public void setSpikeData(int[] spikeData) {
		this.spikeData = spikeData;
	}
	public double getSpikePerSec() {
		return spikePerSec;
	}
	public void setSpikePerSec(double spikePerSec) {
		this.spikePerSec = spikePerSec;
	}
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
	public long getTaskId() {
		return taskId;
	}
	public void setTaskId(long taskId) {
		this.taskId = taskId;
	}
}
