package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class visualTrial extends Trial{
	
	int[] stimObjData = {2};
	int[] eStimObjData = {1};
	
	static {
		s = new XStream();
		s.alias("StimSpec", visualTrial.class);
	}
	
	public visualTrial() {
		//Empty Constructor
	}
	
	public visualTrial(int[] stimObjData) {
		//stimObj Constructor
		this.stimObjData = stimObjData;
	}
}
