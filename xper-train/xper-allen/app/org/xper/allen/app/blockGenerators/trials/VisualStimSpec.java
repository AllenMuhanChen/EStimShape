package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class VisualStimSpec extends Trial{
	@XStreamAlias("targetEyeWinSize")
	double targetEyeWinSize;
	@XStreamAlias("stimObjData")
	long[] stimObjData;
	@XStreamAlias("eStimObjData")
	long[] eStimObjData;
	@XStreamAlias("eStimObjChans")
	int[] eStimObjChans;

	public VisualStimSpec() {
		//Empty Constructor
	}
	
	public VisualStimSpec(long[] stimObjData, double targetEyeWinSize) {
		//stimObj Constructor
		this.targetEyeWinSize = targetEyeWinSize; 
		this.stimObjData = stimObjData;
		this.eStimObjData = new long[] {1};
		this.eStimObjChans = new int[] {};
		
		
		s = new XStream();
		s.alias("StimSpec", VisualStimSpec.class);
		s.setMode(XStream.NO_REFERENCES);
	}
	
	@Override
	public String toXml() {
		return s.toXML(this);
	}
}
