package org.xper.db.vo;

public class StimSpecEntry {
	/**
	 * It's the timestamp in microseconds.
	 */
	long stimId;
	/**
	 * Encoded as XML string.
	 */
	String spec;
	public String getSpec() {
		return spec;
	}
	public void setSpec(String spec) {
		this.spec = spec;
	}
	public long getStimId() {
		return stimId;
	}
	public void setStimId(long stimId) {
		this.stimId = stimId;
	}
}
