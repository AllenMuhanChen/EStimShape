package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public abstract class Trial {
	long[] stimObjData;
	long[] eStimObjData;
	
	public long[] getStimObjData() {
		return stimObjData;
	}
	public void setStimObjData(long[] stimObjData) {
		this.stimObjData = stimObjData;
	}
	public long[] getEStimObjData() {
		return eStimObjData;
	}
	public void setEStimObjData(long[] eStimObjData) {
		this.eStimObjData = eStimObjData;
	}
	
	transient static XStream s;
	
	static {
		s = new XStream();
		s.alias("StimSpec", Trial.class);
	}
	
	public String toXml() {
		return Trial.toXml(this);
	}
	
	public static String toXml(Trial trial) {
		return s.toXML(trial);
	}
}
