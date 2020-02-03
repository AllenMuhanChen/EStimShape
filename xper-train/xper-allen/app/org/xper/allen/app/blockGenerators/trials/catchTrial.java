package org.xper.allen.app.blockGenerators.trials;

import com.thoughtworks.xstream.XStream;

public class catchTrial extends Trial{
	
	static {
		s = new XStream();
		s.alias("StimSpec", catchTrial.class);
	}
	
	int[] stimObjData = {1};
	int[] eStimObjData = {1};
}
