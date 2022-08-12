package org.xper.db.vo;

public class TaskDoneEntry {
	long tstamp;
	long taskId;
	int part_done;
	public int getPart_done() {
		return part_done;
	}
	public void setPart_done(int part_done) {
		this.part_done = part_done;
	}
	public long getTaskId() {
		return taskId;
	}
	public void setTaskId(long taskId) {
		this.taskId = taskId;
	}
	public long getTstamp() {
		return tstamp;
	}
	public void setTstamp(long tstamp) {
		this.tstamp = tstamp;
	}
}
