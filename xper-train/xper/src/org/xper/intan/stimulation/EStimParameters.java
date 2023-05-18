package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

import java.util.Collection;
import java.util.HashMap;
import java.util.Map;

public class EStimParameters {

    Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels;

    public EStimParameters(Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels) {
        this.eStimParametersForChannels = eStimParametersForChannels;
    }

    public EStimParameters() {
    }


    static XStream xstream = new XStream();

    static {
        xstream.alias("EStimParameters", EStimParameters.class);
    }

    public static EStimParameters fromXml (String xml) {
        return (EStimParameters)xstream.fromXML(xml);
    }

    public static String toXml (EStimParameters msg) {
        return xstream.toXML(msg);
    }

    public String toXml() {
        return xstream.toXML(this);
    }

    public Map<RHSChannel, ChannelEStimParameters> geteStimParametersForChannels() {
        return eStimParametersForChannels;
    }

    public void seteStimParametersForChannels(Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels) {
        this.eStimParametersForChannels = eStimParametersForChannels;
    }
}