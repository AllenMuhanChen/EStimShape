package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;
import com.thoughtworks.xstream.annotations.XStreamAlias;

public class catchTrial extends Trial{
	
	static {
		s = new XStream();
		s.alias("StimSpec", catchTrial.class);
	}
	
	@XStreamAlias("stimObjData")
	long[] stimObjData = {1};
	@XStreamAlias("eStimObjData")
	long[] eStimObjData = {1};
}
