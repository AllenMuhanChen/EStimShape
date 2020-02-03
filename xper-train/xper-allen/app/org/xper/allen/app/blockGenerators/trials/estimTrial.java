package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class estimTrial extends Trial{
	static {
		s = new XStream();
		s.alias("StimSpec", estimTrial.class);
	}
	int[] stimObjData = {1};
	int[] eStimObjData = {2};
	
	public estimTrial() {
	}
	
	public estimTrial(int[] estimObjData) {
		this.eStimObjData = estimObjData;
	}
	

}
