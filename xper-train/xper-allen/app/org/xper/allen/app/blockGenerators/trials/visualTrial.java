package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class visualTrial extends Trial{
	
	@XStreamAlias("stimObjData")
	long[] stimObjData = {2};
	@XStreamAlias("eStimObjData")
	long[] eStimObjData = {1};
	
	static {
		s = new XStream();
		s.alias("StimSpec", visualTrial.class);
	}
	
	public visualTrial() {
		//Empty Constructor
	}
	
	public visualTrial(long[] stimObjData) {
		//stimObj Constructor
		this.stimObjData = stimObjData;
	}
}
