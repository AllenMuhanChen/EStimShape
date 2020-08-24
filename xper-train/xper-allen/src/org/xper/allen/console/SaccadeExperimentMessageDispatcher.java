package org.xper.allen.console;

import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.vo.TrialContext;
import org.xper.allen.experiment.saccade.*;
public class SaccadeExperimentMessageDispatcher extends TrialExperimentMessageDispatcher implements TargetEventListener{

	@Override
	public void targetOn(long timestamp, TrialContext context) {
		SaccadeExperimentTask currentTask = (SaccadeExperimentTask) context.getCurrentTask();
		
		SaccadeTargetMessage SaccadeTargetMsg = new SaccadeTargetMessage(timestamp, currentTask.getTargetEyeWinCoords(), currentTask.getTargetEyeWinSize(), currentTask.getStimId());
		String msg = SaccadeTargetMsg.toXml();
		enqueue(timestamp, "TargetOn", msg);
		
	}

	@Override
	public void targetOff(long timestamp, TrialContext context) {
		enqueue(timestamp, "TargetOff", "");
		
	}

}
