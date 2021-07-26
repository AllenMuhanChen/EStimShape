package org.xper.allen.saccade.console;

import org.xper.allen.intan.SimpleEStimEventListener;
import org.xper.allen.intan.SimpleEStimMessage;
import org.xper.allen.saccade.*;
import org.xper.allen.saccade.db.vo.SaccadeTrialStatistics;
import org.xper.classic.TrialExperimentMessageDispatcher;
import org.xper.classic.vo.TrialContext;
import org.xper.classic.vo.TrialStatistics;

/**
 * Provides methods for sending "TargetOn" and "TargetOff" messages to database (behmsg).
 * Contains a modified trialStop(), with modified TrialStatistics (SaccadeTrialStatistics)
 * @author Allen Chen
 *
 */
public class SaccadeExperimentMessageDispatcher extends TrialExperimentMessageDispatcher implements TargetEventListener, SimpleEStimEventListener{
	
	protected SaccadeTrialStatistics trialStat = new SaccadeTrialStatistics();

	
	//Target Related Messages:
	public void targetOn(long timestamp, TrialContext context) {
		SaccadeExperimentTask currentTask = (SaccadeExperimentTask) context.getCurrentTask();
		
		SaccadeTargetMessage SaccadeTargetMsg = new SaccadeTargetMessage(timestamp, currentTask.getTargetEyeWinCoords(), currentTask.getTargetEyeWinSize(), currentTask.getStimId());
		String msg = SaccadeTargetMsg.toXml();
		enqueue(timestamp, "TargetOn", msg);
		
	}

	
	public void targetOff(long timestamp) {
		enqueue(timestamp, "TargetOff", "");
		
	}
	
	public void targetSelectionDone(long timestamp) {
		enqueue(timestamp, "TargetSelectionDone", "");
		trialStat.setAllTrialsPASS(trialStat.getAllTrialsPASS()+1);
		}

	public void targetSelectionEyeFail(long timestamp) {
		enqueue(timestamp, "TargetSelectionEyeFail", "");
		trialStat.setTargetSelectionEyeFail(trialStat.getTargetSelectionEyeFail()+1);
	}
	
	public void targetSelectionEyeBreak(long timestamp) {
		enqueue(timestamp, "TargetSelectionEyefail", "");
		trialStat.setTargetSelectionEyeBreak(trialStat.getTargetSelectionEyeBreak()+1);
	}

	//Overriden Messages from TrialExperimentMessageDispatcher, since I need a new SaccadeTrialStatistics. 
	public void trialStop(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialStop", "");
		enqueue(timestamp, "TrialStatistics",
				SaccadeTrialStatistics.toXml(trialStat));
	}
	
	public void eyeInBreak(long timestamp, TrialContext context) {
		enqueue(timestamp, "EyeInBreak", "");
		trialStat.setBrokenTrials(trialStat.getBrokenTrials()+1);
	}

	public void eyeInHoldFail(long timestamp, TrialContext context) {
		enqueue(timestamp, "EyeInHoldFail", "");
		trialStat.setFailedTrials(trialStat.getFailedTrials()+1);
	}

	public void experimentStart(long timestamp) {
		enqueue(timestamp, "ExperimentStart", "");

		trialStat.reset();
	}
	
	public void initialEyeInFail(long timestamp, TrialContext context) {
		enqueue(timestamp, "InitialEyeInFail", "");
		trialStat.setFailedTrials(trialStat.getFailedTrials()+1);
	}
	
	public void trialComplete(long timestamp, TrialContext context) {
		enqueue(timestamp, "TrialComplete", "");
		trialStat.setCompleteTrials(trialStat.getCompleteTrials() + 1);
	}
	
	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		// TODO Auto-generated method stub
		SaccadeExperimentTask currentTask = (SaccadeExperimentTask) context.getCurrentTask();
		
		SimpleEStimMessage simpleEStimMsg = new SimpleEStimMessage(timestamp, currentTask.getTargetEyeWinCoords(), currentTask.getTargetEyeWinSize(), currentTask.getStimId());
		String msg = simpleEStimMsg.toXml();
		enqueue(timestamp, "EStimOn", msg);
	}

}
