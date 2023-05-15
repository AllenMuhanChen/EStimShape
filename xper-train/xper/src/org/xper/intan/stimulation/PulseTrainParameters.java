package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class PulseTrainParameters {

    PulseRepetition pulseRepetition;
    int numRepetitions;
    double pulseTrainPeriod;
    double postStimRefractoryPeriod;

    public PulseTrainParameters(PulseRepetition pulseRepetition, int numRepetitions, double pulseTrainPeriod, double postStimRefractoryPeriod) {
        this.pulseRepetition = pulseRepetition;
        this.numRepetitions = numRepetitions;
        this.pulseTrainPeriod = pulseTrainPeriod;
        this.postStimRefractoryPeriod = postStimRefractoryPeriod;
    }

    public PulseTrainParameters() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("PulseTrainParameters", PulseTrainParameters.class);
    }

    public static PulseTrainParameters fromXml (String xml) {
        return (PulseTrainParameters)xstream.fromXML(xml);
    }

    public static String toXml (PulseTrainParameters msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }
}