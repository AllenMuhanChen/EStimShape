package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class visualTrial extends Trial{
	
	long[] stimObjData = {2};
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
