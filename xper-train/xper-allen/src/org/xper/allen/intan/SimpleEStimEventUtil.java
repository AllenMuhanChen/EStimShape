package org.xper.allen.intan;

import java.util.List;

import org.xper.classic.vo.TrialContext;

public class SimpleEStimEventUtil{

	public static void prepareEStim(long timestamp, List<?extends EStimEventListener> simpleEStimEventListeners, TrialContext currentContext) {
		for (EStimEventListener listener: simpleEStimEventListeners) {
			listener.prepareEStim(timestamp, currentContext);
		}
	}

	public static void fireEStimOn(long timestamp, List<?extends EStimEventListener> simpleEStimEventListeners, TrialContext currentContext) {
		for (EStimEventListener listener: simpleEStimEventListeners) {
			listener.eStimOn(timestamp, currentContext);
		}
	}

}