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

    double calibrationDegree;

    public FixTrainStimSpec() {
    }


    public FixTrainStimSpec(String stimClass, String stimSpec, double calibrationDegree) {
        this.stimClass = stimClass;
        this.stimSpec = stimSpec;
        this.calibrationDegree = calibrationDegree;
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

    public static FixTrainStimSpec fromFixTrainDrawable(FixTrainDrawable<?> drawable, double calibrationDegree) {
        String stimSpec = drawable.getSpec();
        String stimClass = drawable.getClass().getName();

        return new FixTrainStimSpec(stimClass, stimSpec, calibrationDegree);
    }

    public static String getStimSpecFromFixTrainDrawable(FixTrainDrawable<?> drawable, double calibrationDegree ) {
        return FixTrainStimSpec.fromFixTrainDrawable(drawable, calibrationDegree).toXml();
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

    public double getCalibrationDegree() {
        return calibrationDegree;
    }

    public void setCalibrationDegree(double calibrationDegree) {
        this.calibrationDegree = calibrationDegree;
    }
}