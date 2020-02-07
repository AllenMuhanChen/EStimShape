package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class bothTrial extends Trial{
	@XStreamAlias("targetEyeWinSize")
	float targetEyeWinSize;
	@XStreamAlias("stimObjData")
	long[] stimObjData;
	@XStreamAlias("eStimObjData")
	long[] eStimObjData;
	@XStreamAlias("eStimObjChans")
	int[] eStimObjChans;
	
	public bothTrial() {
		//Empty Constructor
	}
	
	public bothTrial(float targetEyeWinSize,long[] stimObjData, long[] estimObjData, int[] eStimObjChans) {
		//stimObj Constructor
		this.targetEyeWinSize = targetEyeWinSize;
		this.eStimObjData = estimObjData;
		this.stimObjData = stimObjData;
		this.eStimObjChans = eStimObjChans;
	}
	
	public bothTrial(long[] stimObjData, long[] estimObjData, int[] eStimObjChans) {
		//stimObj Constructor
		targetEyeWinSize = 4;
		this.stimObjData = stimObjData;
		this.eStimObjData = estimObjData;
		this.eStimObjChans = eStimObjChans;
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
