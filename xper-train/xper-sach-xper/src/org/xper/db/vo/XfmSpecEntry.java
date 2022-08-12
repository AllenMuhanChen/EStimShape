package org.xper.db.vo;

public class XfmSpecEntry {
	long xfmId;
	/**
	 * XML string.
	 */
	String spec;
	public String getSpec() {
		return spec;
	}
	public void setSpec(String spec) {
		this.spec = spec;
	}
	public long getXfmId() {
		return xfmId;
	}
	public void setXfmId(long xfmId) {
		this.xfmId = xfmId;
	}
}
