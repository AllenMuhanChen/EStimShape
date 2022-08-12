package org.xper.db.vo;

public class ExpLogEntry {
	long tstamp;
	String log;
	public String getLog() {
		return log;
	}
	public void setLog(String log) {
		this.log = log;
	}
	public long getTstamp() {
		return tstamp;
	}
	public void setTstamp(long tstamp) {
		this.tstamp = tstamp;
	}
}
