package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class bothTrial extends Trial{
	
	int[] stimObjData = {2};
	int[] eStimObjData = {2};
	
	static {
		s = new XStream();
		s.alias("StimSpec", bothTrial.class);
	}
	
	public bothTrial() {
		//Empty Constructor
	}
	
	public bothTrial(int[] stimObjData, int[] estimObjData) {
		//stimObj Constructor
		this.eStimObjData = estimObjData;
		this.stimObjData = stimObjData;
	}

		
	
}
