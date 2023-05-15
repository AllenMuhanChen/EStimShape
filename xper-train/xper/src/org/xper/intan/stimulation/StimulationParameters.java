package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class StimulationParameters {

    WaveformParameters waveformParameters;
    PulseTrainParameters pulseTrainParameters;

    public StimulationParameters(WaveformParameters waveformParameters, PulseTrainParameters pulseTrainParameters) {
        this.waveformParameters = waveformParameters;
        this.pulseTrainParameters = pulseTrainParameters;
    }

    public StimulationParameters() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("StimulationParameters", StimulationParameters.class);
    }

    public static StimulationParameters fromXml (String xml) {
        return (StimulationParameters)xstream.fromXML(xml);
    }

    public static String toXml (StimulationParameters msg) {
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