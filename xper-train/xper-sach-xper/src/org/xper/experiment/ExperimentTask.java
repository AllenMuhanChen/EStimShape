package org.xper.experiment;


public class ExperimentTask {
	long taskId;
	long stimId;
	long xfmId;
	long genId;
	
	String stimSpec;
	String xfmSpec;
	
	public long getGenId() {
		return genId;
	}
	public void setGenId(long genId) {
		this.genId = genId;
	}
	public long getStimId() {
		return stimId;
	}
	public void setStimId(long stimId) {
		this.stimId = stimId;
	}
	public String getStimSpec() {
		return stimSpec;
	}
	public void setStimSpec(String stimSpec) {
		this.stimSpec = stimSpec;
	}
	public long getTaskId() {
		return taskId;
	}
	public void setTaskId(long taskId) {
		this.taskId = taskId;
	}
	public long getXfmId() {
		return xfmId;
	}
	public void setXfmId(long xfmId) {
		this.xfmId = xfmId;
	}
	public String getXfmSpec() {
		return xfmSpec;
	}
	public void setXfmSpec(String xfmSpec) {
		this.xfmSpec = xfmSpec;
	}
}
