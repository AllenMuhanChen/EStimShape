package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class estimTrial extends Trial{
	
	@XStreamAlias("targetEyeWinSize")
	float targetEyeWinSize;
	@XStreamAlias("stimObjData")
	long[] stimObjData;
	@XStreamAlias("eStimObjData")
	long[] eStimObjData;
	@XStreamAlias("eStimObjChans")
	int[] eStimObjChans;
	
	public estimTrial() {
	}
	
	public estimTrial(long[] estimObjData, int[] eStimObjChans) {
		targetEyeWinSize = 4;
		stimObjData = new long[] {1};
		this.eStimObjData = estimObjData;
		this.eStimObjChans = eStimObjChans;
	}
	
	static {
		s = new XStream();
		s.alias("StimSpec", estimTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	public String toXml() {
		return Trial.toXml(this);
	}
	public static String toXml(estimTrial trial) {
		return s.toXML(trial);
	}
	
}
