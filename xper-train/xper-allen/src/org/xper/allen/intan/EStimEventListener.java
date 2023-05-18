package org.xper.allen.intan;

import org.xper.classic.vo.TrialContext;

public interface EStimEventListener {

	public void eStimOn(long timestamp, TrialContext context);

	public void prepareEStim(long timestamp, TrialContext currentContext);
}