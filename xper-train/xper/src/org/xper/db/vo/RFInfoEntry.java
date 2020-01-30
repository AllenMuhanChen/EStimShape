package org.xper.db.vo;

public class RFInfoEntry {
	long tstamp;
	/**
	 * Encode as XML string.
	 */
	String info;
	public String getInfo() {
		return info;
	}
	public void setInfo(String info) {
		this.info = info;
	}
	public long getTstamp() {
		return tstamp;
	}
	public void setTstamp(long tstamp) {
		this.tstamp = tstamp;
	}
}
