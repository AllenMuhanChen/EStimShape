package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public abstract class Trial {
	int[] stimObjData;
	int[] eStimObjData;
	
	public int[] getStimObjData() {
		return stimObjData;
	}
	public void setStimObjData(int[] stimObjData) {
		this.stimObjData = stimObjData;
	}
	public int[] getEStimObjData() {
		return eStimObjData;
	}
	public void setEStimObjData(int[] eStimObjData) {
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
