package org.xper.allen.nafc.blockgen.procedural;

import com.thoughtworks.xstream.XStream;
import org.xper.allen.nafc.blockgen.NAFCTrialParameters;

public class ProceduralRandGenParameters {
    private NAFCTrialParameters proceduralStimParameters;
    private int numTrials;

    public ProceduralRandGenParameters(NAFCTrialParameters proceduralStimParameters, int numTrials) {
        this.proceduralStimParameters = proceduralStimParameters;
        this.numTrials = numTrials;
    }

    public ProceduralRandGenParameters() {
    }

    public ProceduralStim.ProceduralStimParameters getProceduralStimParameters() {
        return (ProceduralStim.ProceduralStimParameters) proceduralStimParameters;
    }

    static XStream s = new XStream();

    public String toXml() {
        return s.toXML(this);
    }

    public static ProceduralRandGenParameters fromXml(String xml) {
        XStream s = new XStream();
        return (ProceduralRandGenParameters) s.fromXML(xml);
    }

    public int getNumTrials() {
        return numTrials;
    }
}