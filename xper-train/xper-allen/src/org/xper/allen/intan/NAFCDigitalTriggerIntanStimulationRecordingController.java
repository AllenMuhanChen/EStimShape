package org.xper.allen.intan;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.experiment.listener.ExperimentEventListener;
import org.xper.intan.stimulation.EStimParameters;
import org.xper.intan.stimulation.RHSChannel;

import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

import static org.xper.intan.stimulation.ManualTriggerIntanRHS.tcpNameForIntanChannel;

public class NAFCDigitalTriggerIntanStimulationRecordingController extends NAFCTrialIntanStimulationRecordingController {

    private Set<RHSChannel> stimulationChannels;

    @Override
    public void experimentStart(long timestamp) {
        tryConnection();

        stimulationChannels = new HashSet<>();
        for (RHSChannel channel : RHSChannel.values()) {
            try {
                String channelAmps = getIntan().getIntanClient().get(tcpNameForIntanChannel(channel) + ".FirstPhaseAmplitudeMicroAmps");
                System.out.println("Channel: " + channel.toString() + " Amps: " + channelAmps);
                if (!channelAmps.equals("0") &&
                        channelAmps!= null
                        && !channelAmps.equals("parameter")) {
                    stimulationChannels.add(channel);
                }
            } catch (Exception e) {
                System.out.println("Could not get channel amplitude for " + channel.toString() + " " + e.getMessage());
            }

        }
        System.out.println("Stimulation Channels: " + stimulationChannels);
    }


    @Override
    public void prepareEStim(long timestamp, TrialContext context) {
        if (connected & eStimEnabled) {
            NAFCExperimentTask task = (NAFCExperimentTask) context.getCurrentTask();
            String eStimSpec = task.geteStimSpec();
            validEStimParameters = Objects.equals(eStimSpec, "EStimEnabled");
            if (validEStimParameters) {
                System.out.println("EStim Is Enabled");
                for (RHSChannel channel : stimulationChannels) {
                    getIntan().enableStimulationOn(channel);
                }
            } else{
                System.out.println("EStim Is Disabled");
                for (RHSChannel channel : stimulationChannels) {
                    getIntan().disableStimulationOn(channel);
                }
            }
            getIntan().stop();
            getIntan().uploadParameters(stimulationChannels);
            fileNamingStrategy.rename(context.getCurrentTask().getTaskId());
            getIntan().record();
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