package org.xper.allen.intan;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.stimulation.EStimParameters;
import org.xper.intan.stimulation.RHSChannel;

import java.util.Collections;
import java.util.Objects;

public class NAFCDigitalTriggerIntanStimulationRecordingController extends NAFCTrialIntanStimulationRecordingController{

    @Override
    public void prepareEStim(long timestamp, TrialContext context) {
        if (connected & eStimEnabled) {
            NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
            String eStimSpec = task.geteStimSpec();
            validEStimParameters = Objects.equals(eStimSpec, "EStimEnabled");
            if (validEStimParameters) {
                System.out.println("EStim Is Enabled");
                getIntan().enableStimulationOn(RHSChannel.A025);
            } else{
                System.out.println("EStim Is Disabled");
                getIntan().disableStimulationOn(RHSChannel.A025);
            }

            getIntan().uploadParameters(Collections.singleton(RHSChannel.A025));

        }
    }

    @Override
    public void eStimOn(long timestamp, TrialContext context) {
        if (connected & eStimEnabled) {
            if (validEStimParameters) {
                System.out.println("Trigger Does Nothing in NAFCDigitalTriggerIntanStimulationRecordingController");
            }
        }
    }
}