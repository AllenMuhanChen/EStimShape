package org.xper.allen.intan;

import org.xper.allen.nafc.experiment.NAFCExperimentTask;
import org.xper.classic.vo.TrialContext;
import org.xper.intan.stimulation.RHSChannel;

import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

import static org.xper.intan.stimulation.ManualTriggerIntanRHS.tcpNameForIntanChannel;

/**
 * This is used if you want to trigger stimulation on Intan with a DIGITAL-IN signal.
 * This controller is intended for the user to specify the EStim Parameters on the Intan GUI internally.
 *
 * The best way to do so inside of IntanRHX is to specify single pulse stim with desired refractory period
 * to define pulse train period, and set trigger source to LEVEL. This way
 * as long as the digital in signal is HIGH, the stimulation will continuously be triggered
 * with the desired pulse train period.
 *
 * This is intended to be used alongside NAFCMarkStimAndEStimTrialDrawingController, which
 * specifies sample on right-marker and choice on left-marker, so this can be pre-set on the RHXGUI
 * to trigger EStim on the sample right-marker. This way, no matter if the monkey aborts trials, the triggers
 * will always stay aligned properly to trigger EStim.
 */
public class NAFCDigitalTriggerIntanStimulationRecordingController extends NAFCIntanStimulationRecordingController {

    private Set<RHSChannel> stimulationChannels;

    @Override
    public void experimentStart(long timestamp) {
        tryConnection();
        identifyStimulationEnabledChannels();
    }

    @Override
    public void trialInit(long timestamp, TrialContext context) {
        if (recordingEnabled && !connected) {
            experimentStart(timestamp);
        }
    }

    /**
     * Based on what's set in the GUI. Essentially looks for any channels with
     * a non-zero amplitude and adds them to the stimulationChannels set.
     */
    private void identifyStimulationEnabledChannels() {
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
            getIntan().stop(); //needed to use uploadParameters
            getIntan().uploadParameters(stimulationChannels); //needed to update the stimulation parameters
            fileNamingStrategy.rename(context.getCurrentTask().getTaskId());
            getIntan().waitForUpload();
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