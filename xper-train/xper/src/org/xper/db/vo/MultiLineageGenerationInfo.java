package org.xper.db.vo;

import com.thoughtworks.xstream.XStream;

/**
 * Copied into org.xper.sach.vo from org.xper.db.vo by Allen Chen
 */
public class MultiLineageGenerationInfo extends GenerationInfo{
	long genId;
	int taskCount;
	int stimPerLinCount;
	int repsPerStim;
	int stimPerTrial;
	boolean useStereoRenderer = false;
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("GenerationInfo", MultiLineageGenerationInfo.class);
	}
	
	public String toXml () {
		return MultiLineageGenerationInfo.toXml(this);
	}
	
	public static String toXml (MultiLineageGenerationInfo genInfo) {
		return s.toXML(genInfo);
	}
	
	public static MultiLineageGenerationInfo fromXml (String xml) {
		MultiLineageGenerationInfo g = (MultiLineageGenerationInfo)s.fromXML(xml);
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
	
	public int getStimPerLinCount() {
		return stimPerLinCount;
	}

	public void setStimPerLinCount(int stimPerLinCount) {
		this.stimPerLinCount = stimPerLinCount;
	}
	
	public int getRepsPerStim() {
		return repsPerStim;
	}

	public void setRepsPerStim(int repsPerStim) {
		this.repsPerStim = repsPerStim;
	}
	
	public int getStimPerTrial() {
		return stimPerTrial;
	}

	public void setStimPerTrial(int stimPerTrial) {
		this.stimPerTrial = stimPerTrial;
	}
	
	public boolean getUseStereoRenderer() {
		return useStereoRenderer;
	}

	public void setUseStereoRenderer(boolean useStereoRenderer) {
		this.useStereoRenderer = useStereoRenderer;
	}
	
}
