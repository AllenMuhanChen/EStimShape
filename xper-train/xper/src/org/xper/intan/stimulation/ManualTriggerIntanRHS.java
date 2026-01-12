package org.xper.intan.stimulation;

import org.xper.Dependency;
import org.xper.intan.IntanRHD;
import org.xper.util.ThreadUtil;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;

/**
 * Provides experiment-relevant control of Intan for stimulation and recording
 *
 * This class should be used for when the user wants to manually trigger stimulation with java code (and the f1 key)
 */
public class ManualTriggerIntanRHS extends IntanRHD {
    public static final String DIGITAL_TRIGGER = "DigitalIn01";

    static List<String> ports;
    static List<String> channelNums;
    static{

        ports = new ArrayList<>();
        ports.add("a");
        ports.add("b");
        ports.add("c");
        ports.add("d");

        channelNums = new ArrayList<>();
        channelNums.add("000");
        channelNums.add("001");
        channelNums.add("002");
        channelNums.add("003");
        channelNums.add("004");
        channelNums.add("005");
        channelNums.add("006");
        channelNums.add("007");
        channelNums.add("008");
        channelNums.add("009");
        channelNums.add("010");
        channelNums.add("011");
        channelNums.add("012");
        channelNums.add("013");
        channelNums.add("014");
        channelNums.add("015");
        channelNums.add("016");
        channelNums.add("017");
        channelNums.add("018");
        channelNums.add("019");
        channelNums.add("020");
        channelNums.add("021");
        channelNums.add("022");
        channelNums.add("023");
        channelNums.add("024");
        channelNums.add("025");
        channelNums.add("026");
        channelNums.add("027");
        channelNums.add("028");
        channelNums.add("029");
        channelNums.add("030");
        channelNums.add("031");
    }
    /**
     * Default Parameters that are true for every trial and channel throughout the entire experiment
     */
    @Dependency
    Collection<Parameter<Object>> defaultParameters;

    public void setupManualStimulationFor(EStimParameters eStimParameters){
        disableAllStim();

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = eStimParameters.geteStimParametersForChannels();
        for (RHSChannel channel : parametersForChannels.keySet()){
            enableStimulationOn(channel);
            setDefaultParametersOn(channel);
            setManualTriggerSourceOn(channel);

            ChannelEStimParameters channelEStimParameters = parametersForChannels.get(channel);
            setStimPulseTrainParametersOn(channel, channelEStimParameters.getPulseTrainParameters());
            setStimWaveformParametersOn(channel, channelEStimParameters.getWaveformParameters());
            setAmpSettleParametersOn(channel, channelEStimParameters.getAmpSettleParameters());
            setChargeRecoveryParametersOn(channel, channelEStimParameters.getChargeRecoveryParameters());
        }

        uploadParameters(parametersForChannels.keySet());
    }

    public void setupDigitalStimulationFor(EStimParameters eStimParameters){
        stopRecording(); //necessary to upload stim parameters
        disableAllStim();

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = eStimParameters.geteStimParametersForChannels();
        for (RHSChannel channel : parametersForChannels.keySet()){
            enableStimulationOn(channel);
            setDefaultParametersOn(channel);
            setDigitalTriggerSourceOn(channel);

            ChannelEStimParameters channelEStimParameters = parametersForChannels.get(channel);
            setStimPulseTrainParametersOn(channel, channelEStimParameters.getPulseTrainParameters());
            setStimWaveformParametersOn(channel, channelEStimParameters.getWaveformParameters());
            setAmpSettleParametersOn(channel, channelEStimParameters.getAmpSettleParameters());
            setChargeRecoveryParametersOn(channel, channelEStimParameters.getChargeRecoveryParameters());
        }

        uploadParameters();
    }

    public void trigger(){
        intanClient.execute("manualstimtriggerpulse", "f1");
    }


    private void setStimPulseTrainParametersOn(RHSChannel channel, PulseTrainParameters pulseTrainParameters) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".triggeredgeorlevel", pulseTrainParameters.triggerEdgeOrLevel.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".pulseortrain", pulseTrainParameters.pulseRepetition.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".numberofstimpulses", Integer.toString(pulseTrainParameters.numRepetitions));
        intanClient.set(tcpNameForIntanChannel(channel) + ".pulsetrainperiodmicroseconds", Double.toString(pulseTrainParameters.pulseTrainPeriod));
        intanClient.set(tcpNameForIntanChannel(channel) + ".refractoryperiodmicroseconds", Double.toString(pulseTrainParameters.postStimRefractoryPeriod));
        intanClient.set(tcpNameForIntanChannel(channel) + ".posttriggerdelaymicroseconds", Double.toString(pulseTrainParameters.postTriggerDelay));
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

    private void setAmpSettleParametersOn(RHSChannel channel, AmpSettleParameters ampSettleParameters){
        if (ampSettleParameters == null){
            return;
        }
        intanClient.set(tcpNameForIntanChannel(channel) + ".enableampsettle", ampSettleParameters.enableAmpSettle.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".prestimampsettlemicroseconds", ampSettleParameters.preStimAmpSettle.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".poststimampsettlemicroseconds", ampSettleParameters.postStimAmpSettle.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".maintainampsettle", ampSettleParameters.maintainAmpSettleDuringPulseTrain.toString());

    }

    private void setChargeRecoveryParametersOn(RHSChannel channel, ChargeRecoveryParameters chargeRecoveryParameters) {
        if (chargeRecoveryParameters == null) {
            return;
        }
        intanClient.set(tcpNameForIntanChannel(channel) + ".enablechargerecovery", chargeRecoveryParameters.enableChargeRecovery.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".poststimchargerecovonmicroseconds", chargeRecoveryParameters.postStimChargeRecoveryOn.toString());
        intanClient.set(tcpNameForIntanChannel(channel) + ".poststimchargerecovoffmicroseconds", chargeRecoveryParameters.postStimChargeRecoveryOff.toString());
    }

    public void uploadParameters(Collection<RHSChannel> channels){
        for (RHSChannel channel : channels){
            waitForUpload();
            intanClient.execute("uploadstimparameters", tcpNameForIntanChannel(channel));
        }
        waitForUpload();
    }

    public void uploadParameters(){
        waitForUpload();
        intanClient.execute("uploadstimparameters");
        waitForUpload();
    }

    public void enableStimulationOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".stimenabled", "true");
    }

    public void disableStimulationOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".stimenabled", "false");
    }

    public void disableAllStim(){

        List<String> channelNums = this.channelNums;
        for (String port : ports){

            String out;
            int numChannels;
            while (true){
                ThreadUtil.sleep(100);
                out = intanClient.get(port + ".numberamplifierchannels");
                try {
                    numChannels = Integer.parseInt(out);
                } catch(NumberFormatException e) {
                    continue;
                }
                break;
            }
            if (numChannels > 0){
                for (String channel : channelNums){
                    String channelTcpName = port+"-"+channel;
                    intanClient.set(channelTcpName+".stimenabled", "false");
                }
            }

        }

    }
    private void setDefaultParametersOn(RHSChannel channel) {
        for (Parameter parameter : defaultParameters){
            intanClient.set(tcpNameForIntanChannel(channel) + "." + parameter.getKey().toLowerCase(), parameter.getValue().toString().toLowerCase());
        }
    }

    private void setManualTriggerSourceOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".source", "keypressf1");
    }

    private void setDigitalTriggerSourceOn(RHSChannel channel) {
        intanClient.set(tcpNameForIntanChannel(channel) + ".source", DIGITAL_TRIGGER);
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