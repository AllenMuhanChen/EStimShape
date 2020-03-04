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
	
	public visualTrial(long[] stimObjData, int targetEyeWinSize) {
		//stimObj Constructor
		this.targetEyeWinSize = targetEyeWinSize; 
		this.stimObjData = stimObjData;
		this.eStimObjData = new long[] {1};
		this.eStimObjChans = new int[] {};
		
		
		s = new XStream();
		s.alias("StimSpec", visualTrial.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	@Override
	public String toXml() {
		return s.toXML(this);
	}
}
