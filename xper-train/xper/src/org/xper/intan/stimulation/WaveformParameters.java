package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class WaveformParameters {
    StimulationShape shape;
    StimulationPolarity polarity;
    double d1;
    double d2;
    double dp;
    double a1;
    double a2;

    public WaveformParameters(StimulationShape shape, StimulationPolarity polarity, double d1, double d2, double dp, double a1, double a2) {
        this.shape = shape;
        this.polarity = polarity;
        this.d1 = d1;
        this.d2 = d2;
        this.dp = dp;
        this.a1 = a1;
        this.a2 = a2;
    }

    public WaveformParameters() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("WaveformParameters", WaveformParameters.class);
    }

    public static WaveformParameters fromXml (String xml) {
        return (WaveformParameters)xstream.fromXML(xml);
    }

    public static String toXml (WaveformParameters msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }
}