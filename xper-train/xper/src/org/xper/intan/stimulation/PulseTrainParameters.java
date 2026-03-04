package org.xper.intan.stimulation;

import com.thoughtworks.xstream.XStream;

public class PulseTrainParameters {

    PulseRepetition pulseRepetition;
    int numRepetitions;
    double pulseTrainPeriod;
    double postStimRefractoryPeriod;
    TriggerEdgeOrLevel triggerEdgeOrLevel;
    double postTriggerDelay = 0;

    public PulseTrainParameters(PulseRepetition pulseRepetition, int numRepetitions, double pulseTrainPeriod, double postStimRefractoryPeriod, TriggerEdgeOrLevel triggerEdgeOrLevel, double postTriggerDelay) {
        this.pulseRepetition = pulseRepetition;
        this.numRepetitions = numRepetitions;
        this.pulseTrainPeriod = pulseTrainPeriod;
        this.postStimRefractoryPeriod = postStimRefractoryPeriod;
        this.triggerEdgeOrLevel = triggerEdgeOrLevel;
        this.postTriggerDelay = postTriggerDelay;

        if (pulseRepetition == PulseRepetition.SinglePulse){
            //default values if single pulse is selected
            this.numRepetitions = 2;
            this.pulseTrainPeriod = 10000;
        }
    }

    public PulseTrainParameters(PulseTrainParameters pulseTrainParameters) {
        this.pulseRepetition = pulseTrainParameters.pulseRepetition;
        this.numRepetitions = pulseTrainParameters.numRepetitions;
        this.pulseTrainPeriod = pulseTrainParameters.pulseTrainPeriod;
        this.postStimRefractoryPeriod = pulseTrainParameters.postStimRefractoryPeriod;
        this.triggerEdgeOrLevel = pulseTrainParameters.triggerEdgeOrLevel;
        this.postTriggerDelay = pulseTrainParameters.postTriggerDelay;
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

    public PulseRepetition getPulseRepetition() {
        return pulseRepetition;
    }

    public void setPulseRepetition(PulseRepetition pulseRepetition) {
        this.pulseRepetition = pulseRepetition;
    }

    public int getNumRepetitions() {
        return numRepetitions;
    }

    public void setNumRepetitions(int numRepetitions) {
        this.numRepetitions = numRepetitions;
    }

    public double getPulseTrainPeriod() {
        return pulseTrainPeriod;
    }

    public void setPulseTrainPeriod(double pulseTrainPeriod) {
        this.pulseTrainPeriod = pulseTrainPeriod;
    }

    public double getPostStimRefractoryPeriod() {
        return postStimRefractoryPeriod;
    }

    public void setPostStimRefractoryPeriod(double postStimRefractoryPeriod) {
        this.postStimRefractoryPeriod = postStimRefractoryPeriod;
    }

    public TriggerEdgeOrLevel getTriggerEdgeOrLevel() {
        return triggerEdgeOrLevel;
    }

    public void setTriggerEdgeOrLevel(TriggerEdgeOrLevel triggerEdgeOrLevel) {
        this.triggerEdgeOrLevel = triggerEdgeOrLevel;
    }

    public double getPostTriggerDelay() {
        return postTriggerDelay;
    }

    public void setPostTriggerDelay(double postTriggerDelay) {
        this.postTriggerDelay = postTriggerDelay;
    }


}