package org.xper.allen.intan;

import org.xper.allen.saccade.SaccadeExperimentTask;
import org.xper.classic.TrialEventListener;
import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.vo.TrialContext;

public class SimpleEStimMessageDispatcher extends TrialExperimentMessageDispatcher implements SimpleEStimEventListener{

	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		// TODO Auto-generated method stub
		SaccadeExperimentTask currentTask = (SaccadeExperimentTask) context.getCurrentTask();
		
		SimpleEStimMessage simpleEStimMsg = new SimpleEStimMessage(timestamp, currentTask.getTargetEyeWinCoords(), currentTask.getTargetEyeWinSize(), currentTask.getStimId());
		String msg = simpleEStimMsg.toXml();
		enqueue(timestamp, "EStimOn", msg);
	}


}
