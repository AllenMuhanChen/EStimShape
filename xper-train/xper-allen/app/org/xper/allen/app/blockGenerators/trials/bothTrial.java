package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class bothTrial extends Trial{
	@XStreamAlias("stimObjData")
	long[] stimObjData = {2};
	@XStreamAlias("eStimObjData")
	long[] eStimObjData = {2};
	@XStreamAlias("eStimObjChan")
	int[] eStimObjChan;
	
	static {
		s = new XStream();
		s.alias("StimSpec", bothTrial.class);
	}
	
	public bothTrial() {
		//Empty Constructor
	}
	
	public bothTrial(long[] stimObjData, long[] estimObjData, int[] eStimObjChans) {
		//stimObj Constructor
		this.eStimObjData = estimObjData;
		this.stimObjData = stimObjData;
		this.eStimObjChan = eStimObjChans;
	}

		
	
}
