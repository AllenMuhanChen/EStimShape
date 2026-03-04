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

    public WaveformParameters(WaveformParameters waveformParameters) {
        this.shape = waveformParameters.shape;
        this.polarity = waveformParameters.polarity;
        this.d1 = waveformParameters.d1;
        this.d2 = waveformParameters.d2;
        this.dp = waveformParameters.dp;
        this.a1 = waveformParameters.a1;
        this.a2 = waveformParameters.a2;
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

    public StimulationShape getShape() {
        return shape;
    }

    public void setShape(StimulationShape shape) {
        this.shape = shape;
    }

    public StimulationPolarity getPolarity() {
        return polarity;
    }

    public void setPolarity(StimulationPolarity polarity) {
        this.polarity = polarity;
    }

    public double getD1() {
        return d1;
    }

    public void setD1(double d1) {
        this.d1 = d1;
    }

    public double getD2() {
        return d2;
    }

    public void setD2(double d2) {
        this.d2 = d2;
    }

    public double getDp() {
        return dp;
    }

    public void setDp(double dp) {
        this.dp = dp;
    }

    public double getA1() {
        return a1;
    }

    public void setA1(double a1) {
        this.a1 = a1;
    }

    public double getA2() {
        return a2;
    }

    public void setA2(double a2) {
        this.a2 = a2;
    }
}