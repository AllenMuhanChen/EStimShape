package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class ChannelEStimParameters {

    WaveformParameters waveformParameters;
    PulseTrainParameters pulseTrainParameters;

    public ChannelEStimParameters(WaveformParameters waveformParameters, PulseTrainParameters pulseTrainParameters) {
        this.waveformParameters = waveformParameters;
        this.pulseTrainParameters = pulseTrainParameters;
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

}