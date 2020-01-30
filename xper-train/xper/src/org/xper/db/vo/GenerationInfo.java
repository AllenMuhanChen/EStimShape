package org.xper.db.vo;

import com.thoughtworks.xstream.XStream;

public class GenerationInfo {
	long genId;
	int taskCount;
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("GenerationInfo", GenerationInfo.class);
	}
	
	public String toXml () {
		return GenerationInfo.toXml(this);
	}
	
	public static String toXml (GenerationInfo genInfo) {
		return s.toXML(genInfo);
	}
	
	public static GenerationInfo fromXml (String xml) {
		GenerationInfo g = (GenerationInfo)s.fromXML(xml);
		return g;
	}

	public long getGenId() {
		return genId;
	}

	public void setGenId(long genId) {
		this.genId = genId;
	}

	public int getTaskCount() {
		return taskCount;
	}

	public void setTaskCount(int taskCount) {
		this.taskCount = taskCount;
	}
	
}
