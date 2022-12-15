package org.xper.allen.drawing.composition;

import java.util.List;

public class AllenMStickData {
    List<ShaftData> shaftData;
    List<TerminationData> terminationData;
    List<JunctionData> junctionData;

    public void setMStickData(AllenMatchStick stick){
        AllenMStickData data = stick.getMStickData();




    }

    public List<ShaftData> getShaftData() {
        return shaftData;
    }

    public void setShaftData(List<ShaftData> shaftData) {
        this.shaftData = shaftData;
    }

    public List<TerminationData> getTerminationData() {
        return terminationData;
    }

    public void setTerminationData(List<TerminationData> terminationData) {
        this.terminationData = terminationData;
    }

    public List<JunctionData> getJunctionData() {
        return junctionData;
    }

    public void setJunctionData(List<JunctionData> junctionData) {
        this.junctionData = junctionData;
    }
}
