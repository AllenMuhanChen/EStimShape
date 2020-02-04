package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class catchTrial extends Trial{
	
	static {
		s = new XStream();
		s.alias("StimSpec", catchTrial.class);
	}
	
	long[] stimObjData = {1};
	long[] eStimObjData = {1};
}
