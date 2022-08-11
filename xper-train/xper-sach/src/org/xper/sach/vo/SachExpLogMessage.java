package org.xper.sach.vo;

import org.xper.sach.util.SachIOUtil;

import com.thoughtworks.xstream.XStream;

public class SachExpLogMessage {
	String status;		// start, stop, gen_done, ... ?
	String trialType;	// which trial type (ga, beh, etc) ?
	long genNum;		// which generation?
	long globalGenId;	// this is the genId in TaskToDo db table
	boolean realExp;	// is this a real or mock expt?
	String dateTime;	// readable date/time string
	long timestamp;

	
	public SachExpLogMessage(String status, String trialType, long genNum, long globalGenId, boolean realExp, long timestamp) {
		super();
		setStatus(status);
		setTrialType(trialType);
		setGenNum(genNum);
		setGlobalGenId(globalGenId);
		setRealExp(realExp);
		setTimestamp(timestamp);
	}
	public long getTimestamp() {
		return timestamp;
	}
	public void setTimestamp(long timestamp) {
		this.timestamp = timestamp;
		this.dateTime = SachIOUtil.formatMicroSeconds(timestamp);
	}
	public String getDateTime() {
		return dateTime;
	}
	public String getStatus() {
		return status;
	}
	public void setStatus(String status) {
		this.status = status;
	}
	public String getTrialType() {
		return trialType;
	}
	public void setTrialType(String trialType) {
		this.trialType = trialType;
	}
	public long getGenNum() {
		return genNum;
	}
	public void setGenNum(long genNum) {
		this.genNum = genNum;
	}
	public long getGlobalGenId() {
		return globalGenId;
	}
	public void setGlobalGenId(long genId) {
		this.globalGenId = genId;
	}
	public boolean getRealExp() {
		return realExp;
	}
	public void setRealExp(boolean realExp) {
		this.realExp = realExp;
	}

	static XStream xstream = new XStream();

	static {
		xstream.alias("SachExpLogMessage", SachExpLogMessage.class);
	}
	
	public static SachExpLogMessage fromXml (String xml) {
		return (SachExpLogMessage)xstream.fromXML(xml);
	}
	
	public static String toXml (SachExpLogMessage msg) {
		return xstream.toXML(msg);
	}
}
