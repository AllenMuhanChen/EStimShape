package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class estimTrial extends Trial{
	static {
		s = new XStream();
		s.alias("StimSpec", estimTrial.class);
	}
	@XStreamAlias("stimObjData")
	long[] stimObjData = {1};
	@XStreamAlias("eStimObjData")
	long[] eStimObjData = {2};
	
	public estimTrial() {
	}
	
	public estimTrial(long[] estimObjData, int[] eStimObjChans) {
		this.eStimObjData = estimObjData;
		this.eStimObjChans = eStimObjChans;
	}
	

}
