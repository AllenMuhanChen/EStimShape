package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class visualTrial extends Trial{
	@XStreamAlias("targetEyeWinSize")
	float targetEyeWinSize;
	@XStreamAlias("stimObjData")
	long[] stimObjData;
	@XStreamAlias("eStimObjData")
	long[] eStimObjData;
	@XStreamAlias("eStimObjChans")
	int[] eStimObjChans;

	public visualTrial() {
		//Empty Constructor
	}
	
	public visualTrial(long[] stimObjData) {
		//stimObj Constructor
		targetEyeWinSize = 4; 
		this.stimObjData = stimObjData;
		eStimObjData = new long[] {1};
		eStimObjChans = new int[] {};
	}
	
	static {
		s = new XStream();
		s.alias("StimSpec", visualTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	public String toXml() {
		return Trial.toXml(this);
	}
	public static String toXml(visualTrial trial) {
		return s.toXML(trial);
	}
}
