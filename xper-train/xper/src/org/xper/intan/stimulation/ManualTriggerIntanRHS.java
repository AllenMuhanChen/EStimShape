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

    @Dependency
    public List<String> ports;
    static List<String> channelNums;
    static{
        channelNums = new ArrayList<>();
        for (int i = 0; i <= 31; i++) {
            channelNums.add(String.format("%03d", i));
        }
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
        stop(); //necessary to upload stim parameters
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

    // ───────────────────────────────────────────────
    // Batched methods
    // ───────────────────────────────────────────────

    public void setupManualStimulationForBatched(EStimParameters eStimParameters){
        disableAllStimBatched();

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = eStimParameters.geteStimParametersForChannels();

        List<String> cmds = new ArrayList<>();
        for (RHSChannel channel : parametersForChannels.keySet()){
            String tcpName = tcpNameForIntanChannel(channel);
            cmds.add("set " + tcpName + ".stimenabled true");
            addDefaultParameterCommands(tcpName, cmds);
            cmds.add("set " + tcpName + ".source keypressf1");

            ChannelEStimParameters channelEStimParameters = parametersForChannels.get(channel);
            addPulseTrainCommands(tcpName, channelEStimParameters.getPulseTrainParameters(), cmds);
            addWaveformCommands(tcpName, channelEStimParameters.getWaveformParameters(), cmds);
            addAmpSettleCommands(tcpName, channelEStimParameters.getAmpSettleParameters(), cmds);
            addChargeRecoveryCommands(tcpName, channelEStimParameters.getChargeRecoveryParameters(), cmds);
        }

        intanClient.sendBatch(cmds);
        uploadParameters(parametersForChannels.keySet());
    }
    public void setupDigitalStimulationForBatched(EStimParameters eStimParameters){
        System.out.println("SETTING UP STIMULATION WITH BATCHED");
        long totalStart = System.currentTimeMillis();

        stop();

        long disableStart = System.currentTimeMillis();
        disableAllStimBatched();
        System.out.println("  disableAllStim: " + (System.currentTimeMillis() - disableStart) + " ms");

        Map<RHSChannel, ChannelEStimParameters> parametersForChannels = eStimParameters.geteStimParametersForChannels();

        List<String> cmds = new ArrayList<>();
        for (RHSChannel channel : parametersForChannels.keySet()){
            String tcpName = tcpNameForIntanChannel(channel);
            cmds.add("set " + tcpName + ".stimenabled true");
            addDefaultParameterCommands(tcpName, cmds);
            cmds.add("set " + tcpName + ".source " + DIGITAL_TRIGGER);

            ChannelEStimParameters channelEStimParameters = parametersForChannels.get(channel);
            addPulseTrainCommands(tcpName, channelEStimParameters.getPulseTrainParameters(), cmds);
            addWaveformCommands(tcpName, channelEStimParameters.getWaveformParameters(), cmds);
            addAmpSettleCommands(tcpName, channelEStimParameters.getAmpSettleParameters(), cmds);
            addChargeRecoveryCommands(tcpName, channelEStimParameters.getChargeRecoveryParameters(), cmds);
        }

        long sendStart = System.currentTimeMillis();
        intanClient.sendBatch(cmds);
        System.out.println("  sendBatch: " + (System.currentTimeMillis() - sendStart) + " ms");

        long uploadStart = System.currentTimeMillis();
        uploadParameters();
        System.out.println("  upload: " + (System.currentTimeMillis() - uploadStart) + " ms");

        System.out.println("  TOTAL: " + (System.currentTimeMillis() - totalStart) + " ms");
    }

    public void disableAllStimBatched(){
        List<String> cmds = new ArrayList<>();
        for (String port : ports){
            int numChannels = getPortChannelCount(port);
            if (numChannels > 0){
                for (String channel : channelNums){
                    cmds.add("set " + port + "-" + channel + ".stimenabled false");
                }
            }
        }
        if (!cmds.isEmpty()) {
            intanClient.sendBatch(cmds);
        }
    }

    // ───────────────────────────────────────────────
    // Batch command builders
    // ───────────────────────────────────────────────

    private void addPulseTrainCommands(String tcpName, PulseTrainParameters p, List<String> cmds) {
        cmds.add("set " + tcpName + ".triggeredgeorlevel " + p.triggerEdgeOrLevel);
        cmds.add("set " + tcpName + ".pulseortrain " + p.pulseRepetition);
        cmds.add("set " + tcpName + ".numberofstimpulses " + p.numRepetitions);
        cmds.add("set " + tcpName + ".pulsetrainperiodmicroseconds " + p.pulseTrainPeriod);
        cmds.add("set " + tcpName + ".refractoryperiodmicroseconds " + p.postStimRefractoryPeriod);
        cmds.add("set " + tcpName + ".posttriggerdelaymicroseconds " + p.postTriggerDelay);
    }

    private void addWaveformCommands(String tcpName, WaveformParameters w, List<String> cmds) {
        cmds.add("set " + tcpName + ".shape " + w.shape);
        cmds.add("set " + tcpName + ".polarity " + w.polarity);
        cmds.add("set " + tcpName + ".firstphasedurationmicroseconds " + w.d1);
        cmds.add("set " + tcpName + ".secondphasedurationmicroseconds " + w.d2);
        cmds.add("set " + tcpName + ".interphasedelaymicroseconds " + w.dp);
        cmds.add("set " + tcpName + ".firstphaseamplitudemicroamps " + w.a1);
        cmds.add("set " + tcpName + ".secondphaseamplitudemicroamps " + w.a2);
    }

    private void addAmpSettleCommands(String tcpName, AmpSettleParameters a, List<String> cmds) {
        if (a == null) return;
        cmds.add("set " + tcpName + ".enableampsettle " + a.enableAmpSettle);
        cmds.add("set " + tcpName + ".prestimampsettlemicroseconds " + a.preStimAmpSettle);
        cmds.add("set " + tcpName + ".poststimampsettlemicroseconds " + a.postStimAmpSettle);
        cmds.add("set " + tcpName + ".maintainampsettle " + a.maintainAmpSettleDuringPulseTrain);
    }

    private void addChargeRecoveryCommands(String tcpName, ChargeRecoveryParameters cr, List<String> cmds) {
        if (cr == null) return;
        cmds.add("set " + tcpName + ".enablechargerecovery " + cr.enableChargeRecovery);
        cmds.add("set " + tcpName + ".poststimchargerecovonmicroseconds " + cr.postStimChargeRecoveryOn);
        cmds.add("set " + tcpName + ".poststimchargerecovoffmicroseconds " + cr.postStimChargeRecoveryOff);
    }

    private void addDefaultParameterCommands(String tcpName, List<String> cmds) {
        for (Parameter parameter : defaultParameters){
            cmds.add("set " + tcpName + "." + parameter.getKey().toLowerCase() + " " + parameter.getValue().toString().toLowerCase());
        }
    }

    // ───────────────────────────────────────────────
    // Shared helpers
    // ───────────────────────────────────────────────

    private int getPortChannelCount(String port) {
        while (true) {
            ThreadUtil.sleep(100);
            String out = intanClient.get(port + ".numberamplifierchannels");
            try {
                return Integer.parseInt(out);
            } catch (NumberFormatException e) {
                // retry
            }
        }
    }

    public void trigger(){
        intanClient.execute("manualstimtriggerpulse", "f1");
    }

    // ───────────────────────────────────────────────
    // Original individual-set methods (kept for compatibility)
    // ───────────────────────────────────────────────

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

    public List<String> getPorts() {
        return ports;
    }

    public void setPorts(List<String> ports) {
        this.ports = ports;
    }
}