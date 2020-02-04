package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class bothTrial extends Trial{
	
	long[] stimObjData = {2};
	long[] eStimObjData = {2};
	
	static {
		s = new XStream();
		s.alias("StimSpec", bothTrial.class);
	}
	
	public bothTrial() {
		//Empty Constructor
	}
	
	public bothTrial(long[] stimObjData, long[] estimObjData) {
		//stimObj Constructor
		this.eStimObjData = estimObjData;
		this.stimObjData = stimObjData;
	}

		
	
}
