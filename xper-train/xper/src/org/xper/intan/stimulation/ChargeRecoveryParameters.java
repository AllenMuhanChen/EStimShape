package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class ChargeRecoveryParameters {
    Boolean enableChargeRecovery = false;
    Double postStimChargeRecoveryOn = 0.0;
    Double postStimChargeRecoveryOff = 0.0;

    public ChargeRecoveryParameters(Boolean enableChargeRecovery, Double postStimChargeRecoveryOn, Double postStimChargeRecoveryOff) {
        this.enableChargeRecovery = enableChargeRecovery;
        this.postStimChargeRecoveryOn = postStimChargeRecoveryOn;
        this.postStimChargeRecoveryOff = postStimChargeRecoveryOff;
    }

    public ChargeRecoveryParameters(ChargeRecoveryParameters chargeRecoveryParameters) {
        this.enableChargeRecovery = chargeRecoveryParameters.enableChargeRecovery;
        this.postStimChargeRecoveryOn = chargeRecoveryParameters.postStimChargeRecoveryOn;
        this.postStimChargeRecoveryOff = chargeRecoveryParameters.postStimChargeRecoveryOff;
    }

    public ChargeRecoveryParameters() {
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("ChargeRecoveryParameters", ChargeRecoveryParameters.class);
    }

    public static ChargeRecoveryParameters fromXml (String xml) {
        return (ChargeRecoveryParameters) xstream.fromXML(xml);
    }

    public static String toXml (ChargeRecoveryParameters msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }

    public Boolean getEnableChargeRecovery() {
        return enableChargeRecovery;
    }

    public void setEnableChargeRecovery(Boolean enableChargeRecovery) {
        this.enableChargeRecovery = enableChargeRecovery;
    }

    public Double getPostStimChargeRecoveryOn() {
        return postStimChargeRecoveryOn;
    }

    public void setPostStimChargeRecoveryOn(Double postStimChargeRecoveryOn) {
        this.postStimChargeRecoveryOn = postStimChargeRecoveryOn;
    }

    public Double getPostStimChargeRecoveryOff() {
        return postStimChargeRecoveryOff;
    }

    public void setPostStimChargeRecoveryOff(Double postStimChargeRecoveryOff) {
        this.postStimChargeRecoveryOff = postStimChargeRecoveryOff;
    }
}
