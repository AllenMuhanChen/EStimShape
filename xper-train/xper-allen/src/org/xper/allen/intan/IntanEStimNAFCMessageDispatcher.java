package org.xper.allen.intan;

import org.xper.Dependency;
import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.IntanRecordingSlideMessageDispatcher;
import org.xper.intan.stimulation.*;

import java.util.Collection;
import java.util.Map;

public class IntanEStimNAFCMessageDispatcher extends IntanRecordingSlideMessageDispatcher implements EStimEventListener
{
	@Dependency
	IntanStimulationController intanStimulationController;


	@Override
	public void trialInit(long timestamp, TrialContext context) {
		if (connected) {
			long trialName = context.getCurrentTask().getTaskId();
			fileNamingStrategy.rename(trialName);
			getIntanController().record();

			Map<RHSChannel, Collection<Parameter<Object>>> parametersForChannels;
			NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
			String eStimSpec = task.geteStimSpec();
			try {
				EStimParameters eStimParameters = EStimParameters.fromXml(eStimSpec);
				intanStimulationController.setupStimulationFor(eStimParameters);

			} catch (Exception e) {
				e.printStackTrace();
				System.err.println("Could not parse eStimSpec");
			}

		}
	}

	@Override
	public void eStimOn(long timestamp, TrialContext context) {
		intanStimulationController.trigger();
	}




}