package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class catchTrial extends Trial{
	@XStreamAlias("targetEyeWinSize")
	float targetEyeWinSize;
	@XStreamAlias("stimObjData")
	long[] stimObjData;
	@XStreamAlias("eStimObjData")
	long[] eStimObjData;
	@XStreamAlias("eStimObjChans")
	int[] eStimObjChans;
	
	public catchTrial() {
		targetEyeWinSize = 4;
		stimObjData = new long[] {1};
		eStimObjData = new long[] {1};
	}
	
	static {
		s = new XStream();
		s.alias("StimSpec", bothTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	public String toXml() {
		return Trial.toXml(this);
	}
	public static String toXml(bothTrial trial) {
		return s.toXML(trial);
	}
	

}
