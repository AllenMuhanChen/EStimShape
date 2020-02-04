package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class estimTrial extends Trial{
	static {
		s = new XStream();
		s.alias("StimSpec", estimTrial.class);
	}
	long[] stimObjData = {1};
	long[] eStimObjData = {2};
	
	public estimTrial() {
	}
	
	public estimTrial(long[] estimObjData) {
		this.eStimObjData = estimObjData;
	}
	

}
