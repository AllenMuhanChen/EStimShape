package org.xper.db.vo;

public class TaskSpikeRate {
	long taskId;
	/**
	 * spike per second.
	 */
	double spikeRate;
	public double getSpikeRate() {
		return spikeRate;
	}
	public void setSpikeRate(double spikeRate) {
		this.spikeRate = spikeRate;
	}
	public long getTaskId() {
		return taskId;
	}
	public void setTaskId(long taskId) {
		this.taskId = taskId;
	}
}
