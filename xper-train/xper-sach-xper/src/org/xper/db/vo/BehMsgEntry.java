package org.xper.db.vo;

public class BehMsgEntry {
	long tstamp;

	String type;

	String msg;

	public String getMsg() {
		return msg;
	}

	public void setMsg(String msg) {
		this.msg = msg;
	}

	public long getTstamp() {
		return tstamp;
	}

	public void setTstamp(long tstamp) {
		this.tstamp = tstamp;
	}

	public String getType() {
		return type;
	}

	public void setType(String type) {
		this.type = type;
	}
}
