package org.xper.sach.vo;

import com.thoughtworks.xstream.XStream;
import org.xper.db.vo.GenerationInfo;

/**
 * Copied into org.xper.sach.vo from org.xper.db.vo by Allen Chen
 */
public class SachGenerationInfo extends GenerationInfo{
	long genId;
	int taskCount;
	int stimPerLinCount;
	int repsPerStim;
	int stimPerTrial;
	boolean useStereoRenderer = false;
	
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
	
	public static SachGenerationInfo fromXml (String xml) {
		SachGenerationInfo g = (SachGenerationInfo)s.fromXML(xml);
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
