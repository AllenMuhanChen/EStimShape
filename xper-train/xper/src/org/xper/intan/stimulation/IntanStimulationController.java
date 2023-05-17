package org.xper.intan.stimulation;

import org.xper.Dependency;
import org.xper.intan.IntanRecordingController;

import java.util.Collection;
import java.util.Map;

/**
 * Provides experiment-relevant control of Intan for stimulation and recording
 */
public class IntanStimulationController extends IntanRecordingController {


    /**
     * Default Parameters that are true for every trial and channel throughout the entire experiment
     */
    @Dependency
    Collection<Parameter<Object>> defaultParameters;

    public void setupStimulationFor(Map<RHSChannel, Collection<Parameter<Object>>> parametersForChannel){
        for (RHSChannel channel : parametersForChannel.keySet()){
            enableStimulationOn(channel);
            setDefaultParametersOn(channel);
            setTriggerSourceOn(channel);
            setStimWaveformParametersOn(channel, parametersForChannel.get(channel));
        }

        uploadParameters(parametersForChannel.keySet());
    }

    private void uploadParameters(Collection<RHSChannel> channels){
        for (RHSChannel channel : channels){
            intanClient.execute("uploadstimparameters", tcpNameForIntanChannel(channel));
        }
    }


    public void trigger(){
        intanClient.execute("manualstimtriggerpulse f1");

    }

    private void enableStimulationOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".stimenabled", "true");

    }

    private void setDefaultParametersOn(RHSChannel channel) {
        for (Parameter parameter : defaultParameters){
            intanClient.set(tcpNameForIntanChannel(channel) + "." + parameter.getKey().toLowerCase(), parameter.getValue().toString().toLowerCase());
        }
    }

    private void setTriggerSourceOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".source", "keypressf1");
    }

    private void setStimWaveformParametersOn(RHSChannel channel, Collection<Parameter<Object>> stimulationParameters){
        for (Parameter parameter : stimulationParameters){
            intanClient.set(tcpNameForIntanChannel(channel) + "." + parameter.getKey().toLowerCase(), parameter.getValue().toString().toLowerCase());
        }
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