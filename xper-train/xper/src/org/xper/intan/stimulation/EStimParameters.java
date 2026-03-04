package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.function.BiConsumer;

/**
 * When building EStimParameters, DO NOT call the getter on the eStimParametersForChannels and modify.
 * Instead, use put(Channel, Parameters) method, or build the map first and then construct with it.
 * Both of these will ensure deep copies are used.
 * We don't want references in the xml or floating around because they are liable to lead to bugs.
 */
public class EStimParameters {

    private Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels = new HashMap<>();

    public EStimParameters(Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels) {
        this.eStimParametersForChannels = eStimParametersForChannels;

        //Replace all references with a deep copy
        eStimParametersForChannels.forEach(
                new BiConsumer<RHSChannel, ChannelEStimParameters>() {
                    @Override
                    public void accept(RHSChannel channel, ChannelEStimParameters parameters) {
                        ChannelEStimParameters deepCopiedParameter = new ChannelEStimParameters(parameters);
                        eStimParametersForChannels.put(channel, deepCopiedParameter);
                    }
                }
        );
    }

    public EStimParameters() {
        this.eStimParametersForChannels = new HashMap<>();
    }

    /**
     * Deep Copy Constructor
     * @param eStimParameters
     */
    public EStimParameters(EStimParameters eStimParameters) {
        this.eStimParametersForChannels = new HashMap<>();
        for (Map.Entry<RHSChannel, ChannelEStimParameters> entry : eStimParameters.eStimParametersForChannels.entrySet()) {
            this.eStimParametersForChannels.put(entry.getKey(), new ChannelEStimParameters(entry.getValue()));
        }
    }


    /**
     * Use this to populate the map when building this to ensure deep copy.
     * @param channel
     * @param parameters
     */
    public void put(RHSChannel channel, ChannelEStimParameters parameters){
        eStimParametersForChannels.put(channel, new ChannelEStimParameters(parameters));
    }

    static XStream xstream = new XStream();

    static {
        xstream.alias("EStimParameters", EStimParameters.class);
        xstream.setMode(XStream.NO_REFERENCES);
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
        return Collections.unmodifiableMap(eStimParametersForChannels);
    }

    public void seteStimParametersForChannels(Map<RHSChannel, ChannelEStimParameters> eStimParametersForChannels) {
        this.eStimParametersForChannels = eStimParametersForChannels;
    }
}