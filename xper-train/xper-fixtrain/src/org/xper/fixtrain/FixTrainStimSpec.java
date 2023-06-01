package org.xper.fixtrain;

import com.thoughtworks.xstream.XStream;
import org.xper.fixtrain.drawing.FixTrainDrawable;

public class FixTrainStimSpec {
    /**
     * Class name of the FixTrainObject
     */
    String stimClass;
    /**
     * Spec for the FixTrainObject
     */
    String stimSpec;

    public FixTrainStimSpec() {
    }

    public FixTrainStimSpec(String stimClass, String stimSpec) {
        this.stimClass = stimClass;
        this.stimSpec = stimSpec;
    }

    boolean animation = true;
    transient static XStream s;

    static {
        s = new XStream();
        s.alias("StimSpec", FixTrainStimSpec.class);
        s.useAttributeFor("animation", boolean.class);
    }

    public String toXml () {
        return FixTrainStimSpec.toXml(this);
    }

    public static String toXml (FixTrainStimSpec spec) {
        return s.toXML(spec);
    }

    public static FixTrainStimSpec fromXml (String xml) {
        if (xml == null) return null;
        FixTrainStimSpec spec = (FixTrainStimSpec)s.fromXML(xml);
        return spec;
    }

    public static FixTrainStimSpec fromFixTrainDrawable(FixTrainDrawable drawable){
        String stimSpec = drawable.getSpec();
        String stimClass = drawable.getClass().getName();

        return new FixTrainStimSpec(stimClass, stimSpec);
    }

    public static String getStimSpecFromFixTrainDrawable(FixTrainDrawable drawable){
        return FixTrainStimSpec.fromFixTrainDrawable(drawable).toXml();
    }

    public String getStimClass() {
        return stimClass;
    }
    public void setStimClass(String stimClass) {
        this.stimClass = stimClass;
    }
    public String getStimSpec() {
        return stimSpec;
    }
    public void setStimSpec(String stimSpec) {
        this.stimSpec = stimSpec;
    }
}