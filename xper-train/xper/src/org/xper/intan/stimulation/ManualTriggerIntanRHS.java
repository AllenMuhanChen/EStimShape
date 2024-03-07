package org.xper.intan.stimulation;

import org.xper.Dependency;
import org.xper.intan.IntanRHD;

import java.util.Collection;
import java.util.Map;

/**
 * Provides experiment-relevant control of Intan for stimulation and recording
 *
 * This class should be used for when the user wants to manually trigger stimulation with java code (and the f1 key)
 */
public class ManualTriggerIntanRHS extends IntanRHD {


    /**
     * Default Parameters that are true for every trial and channel throughout the entire experiment
     */
    @Dependency
    Collection<Parameter<Object>> defaultParameters;

    public void setupStimulationFor(EStimParameters eStimParameters){
        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = eStimParameters.geteStimParametersForChannels();
        for (RHSChannel channel : parametersForChannels.keySet()){
            enableStimulationOn(channel);
            setDefaultParametersOn(channel);
            setTriggerSourceOn(channel);

            ChannelEStimParameters channelEStimParameters = parametersForChannels.get(channel);
            setStimPulseTrainParametersOn(channel, channelEStimParameters.getPulseTrainParameters());
            setStimWaveformParametersOn(channel, channelEStimParameters.getWaveformParameters());
        }

        uploadParameters(parametersForChannels.keySet());
    }

    public void trigger(){
        intanClient.execute("manualstimtriggerpulse", "f1");
    }


    private void setStimPulseTrainParametersOn(RHSChannel channel, PulseTrainParameters pulseTrainParameters) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".pulseortrain", pulseTrainParameters.pulseRepetition.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".numberofstimpulses", Integer.toString(pulseTrainParameters.numRepetitions));
        intanClient.set(tcpNameForIntanChannel(channel) + ".pulsetrainperiodmicroseconds", Double.toString(pulseTrainParameters.pulseTrainPeriod));
        intanClient.set(tcpNameForIntanChannel(channel) + ".refractoryperiodmicroseconds", Double.toString(pulseTrainParameters.postStimRefractoryPeriod));
    }

    private void setStimWaveformParametersOn(RHSChannel channel, WaveformParameters waveformParameters){
        intanClient.set(tcpNameForIntanChannel(channel) + ".shape", waveformParameters.shape.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".polarity", waveformParameters.polarity.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".firstphasedurationmicroseconds", Double.toString(waveformParameters.d1));
        intanClient.set(tcpNameForIntanChannel(channel) + ".secondphasedurationmicroseconds", Double.toString(waveformParameters.d2));
        intanClient.set(tcpNameForIntanChannel(channel) + ".interphasedelaymicroseconds", Double.toString(waveformParameters.dp));
        intanClient.set(tcpNameForIntanChannel(channel) + ".firstphaseamplitudemicroamps", Double.toString(waveformParameters.a1));
        intanClient.set(tcpNameForIntanChannel(channel) + ".secondphaseamplitudemicroamps", Double.toString(waveformParameters.a2));
    }

    private void uploadParameters(Collection<RHSChannel> channels){
        for (RHSChannel channel : channels){
            intanClient.execute("uploadstimparameters", tcpNameForIntanChannel(channel));
        }
    }


    private void enableStimulationOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".stimenabled", "true");
    }

    private void disableStimulationOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".stimenabled", "false");
    }

    private void setDefaultParametersOn(RHSChannel channel) {
        for (Parameter parameter : defaultParameters){
            intanClient.set(tcpNameForIntanChannel(channel) + "." + parameter.getKey().toLowerCase(), parameter.getValue().toString().toLowerCase());
        }
    }

    private void setTriggerSourceOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".source", "keypressf1");
    }



    public static String tcpNameForIntanChannel(RHSChannel channel){
        // turn ENUM into string all lower case, with hypen between channel
        // letter and numbers
        String channelName = channel.toString().toLowerCase();
        channelName = channelName.replaceAll("([a-z])([0-9])", "$1-$2");
        return channelName;
    }

    public Collection<Parameter<Object>> getDefaultParameters() {
        return defaultParameters;
    }

    public void setDefaultParameters(Collection<Parameter<Object>> defaultParameters) {
        this.defaultParameters = defaultParameters;
    }
}