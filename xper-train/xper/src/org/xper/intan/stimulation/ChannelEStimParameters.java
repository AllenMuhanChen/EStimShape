package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class ChannelEStimParameters {

    WaveformParameters waveformParameters;
    PulseTrainParameters pulseTrainParameters;
    AmpSettleParameters ampSettleParameters;
    ChargeRecoveryParameters chargeRecoveryParameters;


    public ChannelEStimParameters(WaveformParameters waveformParameters, PulseTrainParameters pulseTrainParameters) {
        this.waveformParameters = waveformParameters;
        this.pulseTrainParameters = pulseTrainParameters;
        this.ampSettleParameters = new AmpSettleParameters();
        this.setChargeRecoveryParameters(new ChargeRecoveryParameters());
    }

    public ChannelEStimParameters(WaveformParameters waveformParameters, PulseTrainParameters pulseTrainParameters, AmpSettleParameters ampSettleParameters, ChargeRecoveryParameters chargeRecoveryParameters) {
        this.waveformParameters = waveformParameters;
        this.pulseTrainParameters = pulseTrainParameters;
        this.ampSettleParameters = ampSettleParameters;
        this.setChargeRecoveryParameters(chargeRecoveryParameters);
    }

    public ChannelEStimParameters() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("StimulationParameters", ChannelEStimParameters.class);
    }

    public static ChannelEStimParameters fromXml (String xml) {
        return (ChannelEStimParameters)xstream.fromXML(xml);
    }

    public static String toXml (ChannelEStimParameters msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }

    public WaveformParameters getWaveformParameters() {
        return waveformParameters;
    }

    public void setWaveformParameters(WaveformParameters waveformParameters) {
        this.waveformParameters = waveformParameters;
    }

    public PulseTrainParameters getPulseTrainParameters() {
        return pulseTrainParameters;
    }

    public void setPulseTrainParameters(PulseTrainParameters pulseTrainParameters) {
        this.pulseTrainParameters = pulseTrainParameters;
    }

    public AmpSettleParameters getAmpSettleParameters() {
        return ampSettleParameters;
    }

    public void setAmpSettleParameters(AmpSettleParameters ampSettleParameters) {
        this.ampSettleParameters = ampSettleParameters;
    }

    public ChargeRecoveryParameters getChargeRecoveryParameters() {
        return chargeRecoveryParameters;
    }

    public void setChargeRecoveryParameters(ChargeRecoveryParameters chargeRecoveryParameters) {
        this.chargeRecoveryParameters = chargeRecoveryParameters;
    }
}