package org.xper.allen.nafc.blockgen.procedural;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

public class GenParameters {
    private NAFCTrialParameters proceduralStimParameters;
    private int numTrials;

    public GenParameters(NAFCTrialParameters proceduralStimParameters, int numTrials) {
        this.proceduralStimParameters = proceduralStimParameters;
        this.numTrials = numTrials;
    }

    public GenParameters() {
    }

    public ProceduralStim.ProceduralStimParameters getProceduralStimParameters() {
        return (ProceduralStim.ProceduralStimParameters) proceduralStimParameters;
    }

    static XStream s = new XStream();

    public String toXml() {
        return s.toXML(this);
    }

    public static GenParameters fromXml(String xml) {
        XStream s = new XStream();
        return (GenParameters) s.fromXML(xml);
    }

    public int getNumTrials() {
        return numTrials;
    }
}