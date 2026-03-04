package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class AmpSettleParameters {
    Boolean enableAmpSettle = true;
    Double preStimAmpSettle = 0.0;
    Double postStimAmpSettle = 1000.0;
    Boolean maintainAmpSettleDuringPulseTrain = false;

    public AmpSettleParameters(boolean enableAmpSettle, double preStimAmpSettle, double postStimAmpSettle, boolean maintainAmpSettleDuringPulseTrain) {
        this.enableAmpSettle = enableAmpSettle;
        this.preStimAmpSettle = preStimAmpSettle;
        this.postStimAmpSettle = postStimAmpSettle;
        this.maintainAmpSettleDuringPulseTrain = maintainAmpSettleDuringPulseTrain;
    }

    public AmpSettleParameters(AmpSettleParameters ampSettleParameters) {
        this.enableAmpSettle = ampSettleParameters.enableAmpSettle;
        this.preStimAmpSettle = ampSettleParameters.preStimAmpSettle;
        this.postStimAmpSettle = ampSettleParameters.postStimAmpSettle;
        this.maintainAmpSettleDuringPulseTrain = ampSettleParameters.maintainAmpSettleDuringPulseTrain;
    }

    public AmpSettleParameters() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("AmpSettleParameters", AmpSettleParameters.class);
    }

    public static AmpSettleParameters fromXml (String xml) {
        return (AmpSettleParameters) xstream.fromXML(xml);
    }

    public static String toXml (AmpSettleParameters msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }

    public Boolean getEnableAmpSettle() {
        return enableAmpSettle;
    }

    public void setEnableAmpSettle(Boolean enableAmpSettle) {
        this.enableAmpSettle = enableAmpSettle;
    }

    public Double getPreStimAmpSettle() {
        return preStimAmpSettle;
    }

    public void setPreStimAmpSettle(Double preStimAmpSettle) {
        this.preStimAmpSettle = preStimAmpSettle;
    }

    public Double getPostStimAmpSettle() {
        return postStimAmpSettle;
    }

    public void setPostStimAmpSettle(Double postStimAmpSettle) {
        this.postStimAmpSettle = postStimAmpSettle;
    }

    public Boolean getMaintainAmpSettleDuringPulseTrain() {
        return maintainAmpSettleDuringPulseTrain;
    }

    public void setMaintainAmpSettleDuringPulseTrain(Boolean maintainAmpSettleDuringPulseTrain) {
        this.maintainAmpSettleDuringPulseTrain = maintainAmpSettleDuringPulseTrain;
    }
}
