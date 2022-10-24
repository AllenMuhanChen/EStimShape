package org.xper.allen.intan;

import java.util.List;

import org.xper.classic.vo.TrialContext;
import org.xper.util.EventUtil;

public class SimpleEStimEventUtil{
	
	public static void fireEStimOn(long timestamp, List<?extends SimpleEStimEventListener> simpleEStimEventListeners, TrialContext currentContext) {
		for (SimpleEStimEventListener listener: simpleEStimEventListeners) {
			listener.eStimOn(timestamp, currentContext);
		}
	}

}
