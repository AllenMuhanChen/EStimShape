package org.xper.db.vo;

public class RFInfoEntry {
	long tstamp;
	/**
	 * Encode as XML string.
	 */
	String info;
	/**
	 * Channel this RF was saved for (e.g. "SUPRA-000").
	 */
	String channel;
	/**
	 * Depth in microns driven at which this RF was mapped. 0 denotes the
	 * final/reference recording location.
	 */
	int depth;
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
	public String getChannel() {
		return channel;
	}
	public void setChannel(String channel) {
		this.channel = channel;
	}
	public int getDepth() {
		return depth;
	}
	public void setDepth(int depth) {
		this.depth = depth;
	}
}
