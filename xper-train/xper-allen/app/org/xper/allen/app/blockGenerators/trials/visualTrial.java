package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class visualTrial extends Trial{
	
	@XStreamAlias("stimObjData")
	long[] stimObjData;
	@XStreamAlias("eStimObjData")
	long[] eStimObjData;
	
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
